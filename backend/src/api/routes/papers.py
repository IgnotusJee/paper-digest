from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models import Paper
from ..deps import get_current_user

router = APIRouter(prefix="/api/papers", tags=["papers"])

SORT_COLUMNS = {
    "created_at": Paper.created_at,
    "final_score": Paper.final_score,
    "keyword_score": Paper.keyword_score,
}


@router.get("")
async def list_papers(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    sort: str = Query("created_at", pattern="^(created_at|final_score|keyword_score)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    bucket: str | None = Query(None, pattern="^(venue|arxiv)$"),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(Paper)
    count_query = select(func.count(Paper.id))

    if bucket:
        query = query.where(Paper.bucket == bucket)
        count_query = count_query.where(Paper.bucket == bucket)

    col = SORT_COLUMNS.get(sort, Paper.created_at)
    query = query.order_by(desc(col) if order == "desc" else asc(col))

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    offset = (page - 1) * size
    query = query.offset(offset).limit(size)
    result = await db.execute(query)
    papers = result.scalars().all()

    return {
        "items": [
            {
                "id": p.id,
                "title": p.title,
                "authors": p.authors,
                "venue": p.venue,
                "venue_hint": p.venue_hint,
                "year": p.year,
                "abstract_cn": p.abstract_cn,
                "arxiv_id": p.arxiv_id,
                "final_score": p.final_score,
                "keyword_score": p.keyword_score,
                "bucket": p.bucket,
                "source": p.source,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in papers
        ],
        "total": total,
        "page": page,
        "pages": (total + size - 1) // size if total > 0 else 0,
    }


@router.get("/{paper_id}")
async def get_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    return {
        "id": paper.id,
        "title": paper.title,
        "authors": paper.authors,
        "venue": paper.venue,
        "venue_hint": paper.venue_hint,
        "year": paper.year,
        "abstract_en": paper.abstract_en,
        "abstract_cn": paper.abstract_cn,
        "summary_cn": paper.summary_cn,
        "comments": paper.comments,
        "url": paper.url,
        "pdf_url": paper.pdf_url,
        "arxiv_id": paper.arxiv_id,
        "doi": paper.doi,
        "citation_count": paper.citation_count,
        "source": paper.source,
        "keyword_score": paper.keyword_score,
        "personal_score": paper.personal_score,
        "prefilter_score": paper.prefilter_score,
        "llm_score": paper.llm_score,
        "final_score": paper.final_score,
        "llm_reason": paper.llm_reason,
        "bucket": paper.bucket,
        "pushed": paper.pushed,
        "created_at": paper.created_at.isoformat() if paper.created_at else None,
    }
