import logging
import json
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import APP_CONFIG, get_app_config, load_prompt
from ..database import async_session_factory
from ..models import Paper, Keyword
from .dedup import find_duplicate, merge_into, title_hash
from .fetcher import PaperRaw, fetch_arxiv
from .llm_client import BATCH_SCORE_SCHEMA, LLMChain, LLMUnavailable
from .venue_hint import extract_venue_hint
from .scorer import keyword_match, recency_score, source_prior, prefilter_score
from . import recommender

logger = logging.getLogger(__name__)


def _assign_bucket(venue_hint: str | None, app_config: dict | None = None) -> str:
    app_config = app_config or APP_CONFIG
    buckets_cfg = app_config.get("sources", {}).get("buckets", [])
    venue_bucket = next((b for b in buckets_cfg if b.get("name") == "venue"), None)
    if venue_hint and venue_bucket and venue_bucket.get("include_venue_hint", True):
        return "venue"
    return "arxiv"


async def _upsert_paper(
    raw: PaperRaw, venue_hint: str | None, bucket: str, db: AsyncSession
) -> str:
    try:
        existing = await find_duplicate(raw, db)
        if existing:
            merge_into(existing, raw, venue_hint, bucket)
            return "merged"

        paper = Paper(
            title=raw.title.strip(),
            title_hash=title_hash(raw.title),
            authors=raw.authors,
            abstract_en=raw.abstract,
            comments=raw.comments,
            url=raw.url,
            pdf_url=raw.pdf_url,
            arxiv_id=raw.arxiv_id,
            doi=raw.doi,
            year=int(raw.published[:4]) if raw.published else None,
            venue_hint=venue_hint,
            source="arxiv",
            bucket=bucket,
        )
        db.add(paper)
        return "new"
    except Exception:
        logger.exception("Failed to upsert paper: %s", raw.arxiv_id)
        return "errors"


async def run_fetch_job(fetch_date: date | None = None) -> dict:
    if fetch_date is None:
        fetch_date = date.today() - timedelta(days=1)

    async with async_session_factory() as db:
        app_config = await get_app_config(db)
        buckets_cfg = app_config.get("sources", {}).get("buckets", [])
        arxiv_bucket = next((b for b in buckets_cfg if b.get("name") == "arxiv"), None)
        if not arxiv_bucket or not arxiv_bucket.get("enabled", True):
            logger.info("arXiv bucket disabled, skipping fetch")
            return {"fetched": 0, "new": 0, "merged": 0, "skipped": 0, "errors": 0}

        categories = arxiv_bucket.get("arxiv_categories", [])
        if not categories:
            logger.warning("No arxiv_categories configured")
            return {"fetched": 0, "new": 0, "merged": 0, "skipped": 0, "errors": 0}

        papers = await fetch_arxiv(categories, fetch_date)
        stats = {"fetched": len(papers), "new": 0, "merged": 0, "skipped": 0, "errors": 0}

        for i, raw in enumerate(papers):
            hint = extract_venue_hint(raw.comments, app_config)
            bucket = _assign_bucket(hint, app_config)
            result = await _upsert_paper(raw, hint, bucket, db)
            stats[result] = stats.get(result, 0) + 1

            if (i + 1) % 50 == 0:
                await db.flush()

        try:
            await db.commit()
        except Exception:
            logger.exception("Commit failed, rolling back")
            await db.rollback()

    logger.info("Fetch job done: %s", stats)
    return stats


def assign_bucket(venue: str | None, venue_hint: str | None, app_config: dict | None = None) -> str:
    """Assign paper to venue or arxiv bucket based on venue/venue_hint."""
    app_config = app_config or APP_CONFIG
    buckets_cfg = app_config.get("sources", {}).get("buckets", [])
    venue_bucket = next((b for b in buckets_cfg if b.get("name") == "venue"), None)
    if not venue_bucket:
        return "arxiv"

    venues_list = venue_bucket.get("venues", [])
    if venue and venue in venues_list:
        return "venue"

    if venue_hint and venue_bucket.get("include_venue_hint", True):
        return "venue"

    return "arxiv"


async def run_scoring_job(db: AsyncSession | None = None) -> dict:
    """Recompute derived scores and bucket assignment for every paper."""
    async def _run(session: AsyncSession) -> dict:
        app_config = await get_app_config(session)
        kw_result = await session.execute(select(Keyword))
        keywords = list(kw_result.scalars().all())

        paper_result = await session.execute(select(Paper).order_by(Paper.id))
        papers = list(paper_result.scalars().all())

        scored = 0
        for paper in papers:
            k_score = keyword_match(paper.title, paper.abstract_en, keywords)
            r_score = recency_score(paper.created_at)
            s_score = source_prior(paper.venue, paper.venue_hint, app_config)

            p_score = await recommender.score(paper, session, app_config)

            pf_score = prefilter_score(k_score, p_score, r_score, s_score, p_score != 0.5, app_config)

            paper.keyword_score = k_score
            paper.personal_score = p_score
            paper.prefilter_score = pf_score
            paper.bucket = assign_bucket(paper.venue, paper.venue_hint, app_config)
            scored += 1

        await session.commit()
        logger.info("Scoring job done: %d papers scored", scored)
        return {"scored": scored}

    if db is not None:
        return await _run(db)
    async with async_session_factory() as session:
        return await _run(session)


async def generate_shortlist(db: AsyncSession | None = None) -> list[Paper]:
    """Generate shortlist: per-bucket top (quota × oversample) papers by prefilter_score."""
    async def _run(session: AsyncSession) -> list[Paper]:
        app_config = await get_app_config(session)
        buckets_cfg = app_config.get("sources", {}).get("buckets", [])
        oversample = app_config.get("sources", {}).get("oversample", 3)

        shortlist: list[Paper] = []
        for bucket_cfg in buckets_cfg:
            if not bucket_cfg.get("enabled", True):
                continue
            name = bucket_cfg["name"]
            quota = bucket_cfg.get("quota", 3)
            limit = quota * oversample

            result = await session.execute(
                select(Paper)
                .where(Paper.bucket == name, Paper.pushed == False)
                .order_by(Paper.prefilter_score.desc())
                .limit(limit)
            )
            bucket_papers = list(result.scalars().all())
            shortlist.extend(bucket_papers)

        logger.info("Shortlist generated: %d papers", len(shortlist))
        return shortlist

    if db is not None:
        return await _run(db)
    async with async_session_factory() as session:
        return await _run(session)


def _chunked(items: list[Paper], size: int) -> list[list[Paper]]:
    return [items[idx : idx + size] for idx in range(0, len(items), size)]


def _paper_sort_key(paper: Paper) -> tuple[float, float, int]:
    final_score = paper.final_score if paper.final_score is not None else paper.prefilter_score
    return (final_score, paper.prefilter_score, paper.id or 0)


def _validate_batch_payload(batch: list[Paper], payload: dict) -> None:
    batch_ids = {paper.id for paper in batch}
    returned_ids = [item.get("id") for item in payload.get("papers", [])]
    if set(returned_ids) != batch_ids or len(returned_ids) != len(batch_ids):
        raise ValueError("LLM batch response must contain each paper exactly once")


def _build_batch_score_messages(batch: list[Paper]) -> list[dict]:
    papers_payload = [
        {
            "id": paper.id,
            "title": paper.title,
            "abstract": paper.abstract_en or "",
            "venue": paper.venue,
            "venue_hint": paper.venue_hint,
        }
        for paper in batch
    ]
    return [
        {"role": "system", "content": load_prompt("batch_score")},
        {"role": "user", "content": json.dumps({"papers": papers_payload}, ensure_ascii=False)},
    ]


def _select_final_papers(shortlist: list[Paper], app_config: dict) -> list[Paper]:
    buckets_cfg = app_config.get("sources", {}).get("buckets", [])
    fill_policy = app_config.get("sources", {}).get("fill_policy", "strict")
    daily_total = app_config.get("sources", {}).get("daily_total")
    if not isinstance(daily_total, int) or daily_total < 0:
        daily_total = sum(bucket.get("quota", 0) for bucket in buckets_cfg if bucket.get("enabled", True))

    selected: list[Paper] = []
    selected_ids: set[int] = set()

    for bucket_cfg in buckets_cfg:
        if not bucket_cfg.get("enabled", True):
            continue
        bucket_name = bucket_cfg["name"]
        quota = bucket_cfg.get("quota", 0)
        bucket_papers = sorted(
            [paper for paper in shortlist if paper.bucket == bucket_name],
            key=_paper_sort_key,
            reverse=True,
        )
        for paper in bucket_papers[:quota]:
            if paper.id not in selected_ids:
                selected.append(paper)
                selected_ids.add(paper.id)

    if fill_policy != "spillover" or len(selected) >= daily_total:
        return selected

    remaining = sorted(
        [paper for paper in shortlist if paper.id not in selected_ids],
        key=_paper_sort_key,
        reverse=True,
    )
    selected.extend(remaining[: max(daily_total - len(selected), 0)])
    return selected


async def run_llm_rank(
    shortlist: list[Paper],
    db: AsyncSession,
    llm_chain: LLMChain | None = None,
) -> dict:
    app_config = await get_app_config(db)
    owned_chain = llm_chain is None
    llm_chain = llm_chain or LLMChain(db, app_config=app_config)
    degraded = False
    originals = {
        paper.id: (paper.llm_score, paper.llm_reason, paper.final_score)
        for paper in shortlist
    }

    try:
        batch_size = app_config.get("llm", {}).get("batch_size", 12)
        papers_by_bucket: dict[str, list[Paper]] = defaultdict(list)
        for paper in shortlist:
            papers_by_bucket[paper.bucket or "arxiv"].append(paper)

        for bucket_cfg in app_config.get("sources", {}).get("buckets", []):
            if not bucket_cfg.get("enabled", True):
                continue
            bucket_name = bucket_cfg["name"]
            for batch in _chunked(papers_by_bucket.get(bucket_name, []), batch_size):
                payload = await llm_chain.chat_json(
                    _build_batch_score_messages(batch),
                    BATCH_SCORE_SCHEMA,
                    validator=lambda data, _batch=batch: _validate_batch_payload(_batch, data),
                )
                scored = {item["id"]: item for item in payload["papers"]}
                for paper in batch:
                    result = scored[paper.id]
                    paper.llm_score = float(result["relevance"])
                    paper.llm_reason = result["reason"]
                    paper.final_score = paper.llm_score
    except LLMUnavailable:
        degraded = True
        for paper in shortlist:
            original = originals[paper.id]
            paper.llm_score = original[0]
            paper.llm_reason = original[1]
            paper.final_score = paper.prefilter_score
    finally:
        if owned_chain:
            await llm_chain.aclose()

    if not degraded:
        for paper in shortlist:
            if paper.final_score is None:
                paper.final_score = paper.prefilter_score

    await db.commit()
    selected = _select_final_papers(shortlist, app_config)
    return {
        "papers": selected,
        "selected": selected,
        "degraded": degraded,
    }
