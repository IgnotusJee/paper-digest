import hashlib
import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Paper
from .fetcher import PaperRaw

logger = logging.getLogger(__name__)


def norm_title(t: str) -> str:
    t = t.lower().strip()
    t = re.sub(r"[^\w\s]", "", t)
    return re.sub(r"\s+", " ", t)


def title_hash(t: str) -> str:
    return hashlib.sha256(norm_title(t).encode()).hexdigest()[:16]


async def find_duplicate(raw: PaperRaw, db: AsyncSession) -> Paper | None:
    if raw.doi:
        result = await db.execute(select(Paper).where(Paper.doi == raw.doi))
        existing = result.scalar_one_or_none()
        if existing:
            logger.debug("Dedup hit by doi: %s", raw.doi)
            return existing

    if raw.arxiv_id:
        result = await db.execute(select(Paper).where(Paper.arxiv_id == raw.arxiv_id))
        existing = result.scalar_one_or_none()
        if existing:
            logger.debug("Dedup hit by arxiv_id: %s", raw.arxiv_id)
            return existing

    h = title_hash(raw.title)
    result = await db.execute(select(Paper).where(Paper.title_hash == h))
    existing = result.scalar_one_or_none()
    if existing:
        logger.debug("Dedup hit by title_hash: %s", h)

    return existing


def merge_into(existing: Paper, raw: PaperRaw, venue_hint: str | None, bucket: str) -> None:
    existing.abstract_en = raw.abstract
    existing.comments = raw.comments
    if raw.pdf_url:
        existing.pdf_url = raw.pdf_url
    if raw.url:
        existing.url = raw.url
    existing.authors = raw.authors

    if not existing.venue_hint and venue_hint:
        existing.venue_hint = venue_hint
    if not existing.doi and raw.doi:
        existing.doi = raw.doi
    if not existing.year and raw.published:
        existing.year = int(raw.published[:4])

    target_bucket = "venue" if existing.venue or existing.venue_hint or venue_hint else bucket
    if not existing.bucket or (existing.bucket == "arxiv" and target_bucket == "venue"):
        existing.bucket = target_bucket
