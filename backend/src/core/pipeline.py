import logging
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import APP_CONFIG
from ..database import async_session_factory
from ..models import Paper, Keyword
from .dedup import find_duplicate, merge_into, title_hash
from .fetcher import PaperRaw, fetch_arxiv
from .venue_hint import extract_venue_hint
from .scorer import keyword_match, recency_score, source_prior, prefilter_score
from . import recommender

logger = logging.getLogger(__name__)


def _assign_bucket(venue_hint: str | None) -> str:
    buckets_cfg = APP_CONFIG.get("sources", {}).get("buckets", [])
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

    buckets_cfg = APP_CONFIG.get("sources", {}).get("buckets", [])
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

    async with async_session_factory() as db:
        for i, raw in enumerate(papers):
            hint = extract_venue_hint(raw.comments)
            bucket = _assign_bucket(hint)
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


def assign_bucket(venue: str | None, venue_hint: str | None) -> str:
    """Assign paper to venue or arxiv bucket based on venue/venue_hint."""
    buckets_cfg = APP_CONFIG.get("sources", {}).get("buckets", [])
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
    """Compute scores for all unscored papers (keyword_score=0 and prefilter_score=0)."""
    async def _run(session: AsyncSession) -> dict:
        kw_result = await session.execute(select(Keyword))
        keywords = list(kw_result.scalars().all())

        paper_result = await session.execute(
            select(Paper).where(Paper.prefilter_score == 0.0).order_by(Paper.id)
        )
        papers = list(paper_result.scalars().all())

        scored = 0
        for paper in papers:
            k_score = keyword_match(paper.title, paper.abstract_en, keywords)
            r_score = recency_score(paper.created_at)
            s_score = source_prior(paper.venue, paper.venue_hint)

            p_score = await recommender.score(paper, session)

            pf_score = prefilter_score(k_score, p_score, r_score, s_score, p_score != 0.5)

            paper.keyword_score = k_score
            paper.personal_score = p_score
            paper.prefilter_score = pf_score
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
        buckets_cfg = APP_CONFIG.get("sources", {}).get("buckets", [])
        oversample = APP_CONFIG.get("sources", {}).get("oversample", 3)

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
