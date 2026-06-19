from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models import DigestHistory, Paper
from ..deps import get_current_user

router = APIRouter(prefix="/api/digest", tags=["digest"])


async def _get_digest_for_date(d: date, db: AsyncSession) -> dict:
    result = await db.execute(
        select(DigestHistory)
        .where(DigestHistory.digest_date == d)
        .order_by(DigestHistory.created_at.desc(), DigestHistory.id.desc())
        .limit(1)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="No digest for this date")

    paper_ids = record.paper_ids or []
    papers = []
    if paper_ids:
        result = await db.execute(select(Paper).where(Paper.id.in_(paper_ids)))
        paper_map = {p.id: p for p in result.scalars().all()}
        for pid in paper_ids:
            p = paper_map.get(pid)
            if p:
                summary = p.summary_cn or {}
                papers.append({
                    "id": p.id,
                    "title": p.title,
                    "title_cn": summary.get("title_cn", ""),
                    "abstract_cn": summary.get("abstract_cn", ""),
                    "summary_cn": summary.get("summary_cn", ""),
                    "venue": p.venue,
                    "venue_hint": p.venue_hint,
                    "pdf_url": p.pdf_url,
                    "url": p.url,
                    "final_score": p.final_score,
                    "bucket": p.bucket,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                })

    return {
        "date": str(record.digest_date),
        "papers": papers,
        "bucket_breakdown": record.bucket_breakdown,
        "channel": record.channel,
        "status": record.status,
        "degraded": record.degraded,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


@router.get("")
async def get_today_digest(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await _get_digest_for_date(date.today(), db)


@router.get("/{date_str}")
async def get_digest_by_date(
    date_str: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD")
    return await _get_digest_for_date(d, db)
