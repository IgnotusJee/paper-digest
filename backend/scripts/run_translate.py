"""Manual translation trigger. Usage: python scripts/run_translate.py [--date YYYY-MM-DD] [--limit N]"""
import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from src.config import get_app_config, load_prompt
from src.core.llm_client import BATCH_TRANSLATE_SCHEMA, LLMChain, _parse_or_retry
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session_factory
from src.models import DigestHistory, Paper


def _chunked(items: list[Paper], size: int) -> list[list[Paper]]:
    return [items[idx : idx + size] for idx in range(0, len(items), size)]


def _build_batch_translate_messages(batch: list[Paper]) -> list[dict]:
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
        {"role": "system", "content": load_prompt("batch_translate")},
        {"role": "user", "content": json.dumps({"papers": papers_payload}, ensure_ascii=False)},
    ]


SINGLE_TRANSLATE_SCHEMA = {
    "type": "object",
    "required": ["id", "title_cn", "abstract_cn", "summary_cn"],
    "properties": {
        "id": {"type": "integer"},
        "title_cn": {"type": "string"},
        "abstract_cn": {"type": "string"},
        "summary_cn": {
            "type": "object",
            "required": ["problem", "method", "value"],
            "properties": {
                "problem": {"type": "string"},
                "method": {"type": "string"},
                "value": {"type": "string"},
            },
        },
    },
}


def _parse_translate_payload(raw_text: str) -> dict:
    try:
        return _parse_or_retry(raw_text, BATCH_TRANSLATE_SCHEMA)
    except Exception:
        single = _parse_or_retry(raw_text, SINGLE_TRANSLATE_SCHEMA)
        return {"papers": [single]}


async def _load_target_papers(db: AsyncSession, target_date: date | None, limit: int) -> list[Paper]:
    if target_date:
        result = await db.execute(
            select(DigestHistory)
            .where(DigestHistory.digest_date == target_date)
            .order_by(DigestHistory.created_at.desc(), DigestHistory.id.desc())
            .limit(1)
        )
        digest = result.scalar_one_or_none()
        if digest and digest.paper_ids:
            papers_result = await db.execute(select(Paper).where(Paper.id.in_(digest.paper_ids)))
            paper_map = {paper.id: paper for paper in papers_result.scalars().all()}
            return [paper_map[paper_id] for paper_id in digest.paper_ids if paper_id in paper_map]

    result = await db.execute(
        select(Paper)
        .where(Paper.abstract_cn.is_(None))
        .order_by(Paper.created_at.desc(), Paper.id.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def run_translate_job(target_date: date | None = None, limit: int = 6) -> dict:
    async with async_session_factory() as db:
        app_config = await get_app_config(db)
        papers = await _load_target_papers(db, target_date, limit)
        if not papers:
            return {"translated": 0, "reason": "no_papers"}

        llm_chain = LLMChain(db, app_config=app_config)
        translated = 0

        async def translate_batch(batch: list[Paper]) -> dict:
            messages = _build_batch_translate_messages(batch)
            provider = None
            for provider_name in app_config.get("llm", {}).get("chain", []):
                provider = llm_chain._provider_from_env(provider_name)
                if provider is not None:
                    break
            if provider is None:
                raise RuntimeError("No configured LLM provider for translation")

            raw_text, usage = await llm_chain._post_chat_completion(provider, messages)
            await llm_chain._record_usage(provider, usage)
            return _parse_translate_payload(raw_text)

        try:
            batch_size = app_config.get("llm", {}).get("batch_size", 12)
            for batch in _chunked(papers, batch_size):
                try:
                    payload = await translate_batch(batch)
                    payloads = [payload]
                except Exception:
                    if len(batch) == 1:
                        raise
                    payloads = []
                    for paper in batch:
                        payloads.append(await translate_batch([paper]))

                translated_map = {}
                for payload in payloads:
                    translated_map.update({item["id"]: item for item in payload["papers"]})

                for paper in batch:
                    item = translated_map.get(paper.id)
                    if not item:
                        continue
                    paper.abstract_cn = item["abstract_cn"]
                    paper.summary_cn = {
                        "title_cn": item["title_cn"],
                        "abstract_cn": item["abstract_cn"],
                        "summary_cn": item["summary_cn"],
                    }
                    translated += 1
            await db.commit()
        finally:
            await llm_chain.aclose()

    return {"translated": translated, "papers": len(papers)}


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=date.fromisoformat, default=None)
    parser.add_argument("--limit", type=int, default=6)
    args = parser.parse_args()
    stats = await run_translate_job(args.date, args.limit)
    print(f"[run_translate] Done: {stats}")


if __name__ == "__main__":
    asyncio.run(main())
