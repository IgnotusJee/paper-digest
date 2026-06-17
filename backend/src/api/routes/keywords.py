from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models import Keyword
from ..deps import get_current_user

router = APIRouter(prefix="/api/keywords", tags=["keywords"])


@router.get("")
async def list_keywords(
    category: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(Keyword)
    if category:
        query = query.where(Keyword.category == category)
    query = query.order_by(Keyword.id)
    result = await db.execute(query)
    keywords = result.scalars().all()
    return {
        "items": [
            {
                "id": k.id,
                "keyword": k.keyword,
                "weight": k.weight,
                "category": k.category,
                "aliases": k.aliases,
                "source": k.source,
            }
            for k in keywords
        ],
        "total": len(keywords),
    }


@router.post("", status_code=201)
async def create_keyword(
    body: dict,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    kw_text = body.get("keyword", "").strip()
    if not kw_text:
        raise HTTPException(status_code=400, detail="keyword is required")

    existing = await db.execute(select(Keyword).where(Keyword.keyword == kw_text))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Keyword already exists")

    kw = Keyword(
        keyword=kw_text,
        weight=body.get("weight", 1.0),
        category=body.get("category", "topic"),
        aliases=body.get("aliases"),
        source=body.get("source", "manual"),
    )
    db.add(kw)
    await db.commit()
    await db.refresh(kw)
    return {
        "id": kw.id,
        "keyword": kw.keyword,
        "weight": kw.weight,
        "category": kw.category,
        "aliases": kw.aliases,
        "source": kw.source,
    }


@router.put("/{keyword_id}")
async def update_keyword(
    keyword_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    result = await db.execute(select(Keyword).where(Keyword.id == keyword_id))
    kw = result.scalar_one_or_none()
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")

    if "keyword" in body:
        new_kw = body["keyword"].strip()
        if not new_kw:
            raise HTTPException(status_code=400, detail="keyword cannot be empty")
        dup = await db.execute(select(Keyword).where(Keyword.keyword == new_kw, Keyword.id != keyword_id))
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Keyword already exists")
        kw.keyword = new_kw

    if "weight" in body:
        kw.weight = body["weight"]
    if "category" in body:
        kw.category = body["category"]
    if "aliases" in body:
        kw.aliases = body["aliases"]

    await db.commit()
    await db.refresh(kw)
    return {
        "id": kw.id,
        "keyword": kw.keyword,
        "weight": kw.weight,
        "category": kw.category,
        "aliases": kw.aliases,
        "source": kw.source,
    }


@router.delete("/{keyword_id}", status_code=204)
async def delete_keyword(
    keyword_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    result = await db.execute(select(Keyword).where(Keyword.id == keyword_id))
    kw = result.scalar_one_or_none()
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")
    await db.delete(kw)
    await db.commit()


@router.post("/preset")
async def load_preset(
    body: dict,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    import json
    from pathlib import Path

    preset_name = body.get("name", "").strip()
    if not preset_name:
        raise HTTPException(status_code=400, detail="preset name is required")

    preset_path = Path(__file__).parent.parent.parent.parent / "config" / "presets" / f"{preset_name}.json"
    if not preset_path.exists():
        raise HTTPException(status_code=404, detail=f"Preset '{preset_name}' not found")

    with open(preset_path) as f:
        items = json.load(f)

    loaded = 0
    skipped = 0
    for item in items:
        kw_text = item.get("keyword", "").strip()
        if not kw_text:
            continue
        existing = await db.execute(select(Keyword).where(Keyword.keyword == kw_text))
        if existing.scalar_one_or_none():
            skipped += 1
            continue
        db.add(Keyword(
            keyword=kw_text,
            weight=item.get("weight", 1.0),
            category=item.get("category", "topic"),
            aliases=item.get("aliases"),
            source="preset",
        ))
        loaded += 1

    await db.commit()
    return {"loaded": loaded, "skipped": skipped, "preset": preset_name}
