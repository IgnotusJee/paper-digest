import logging

import fitz
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import get_app_config, load_prompt
from ...core.llm_client import LLMChain
from ...database import get_db
from ...models import Paper
from ..deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/papers", tags=["fulltext"])

CHUNK_SIZE = 8000


def _extract_pdf_text(pdf_url: str) -> str:
    resp = httpx.get(pdf_url, follow_redirects=True, timeout=30)
    resp.raise_for_status()
    doc = fitz.open(stream=resp.content, filetype="pdf")
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n\n".join(pages)


def _chunk_text(text: str, max_chars: int = CHUNK_SIZE) -> list[str]:
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 > max_chars and current:
            chunks.append(current.strip())
            current = para
        else:
            current = current + "\n\n" + para if current else para
    if current.strip():
        chunks.append(current.strip())
    return chunks if chunks else [text]


async def _translate_chunk(llm_chain: LLMChain, app_config: dict, text: str) -> str:
    messages = [
        {"role": "system", "content": load_prompt("fulltext_translate")},
        {"role": "user", "content": text},
    ]
    provider = None
    for name in app_config.get("llm", {}).get("chain", []):
        provider = llm_chain._provider_from_env(name)
        if provider is not None:
            break
    if provider is None:
        raise RuntimeError("No LLM provider available")

    raw_text, usage = await llm_chain._post_chat_completion(provider, messages)
    await llm_chain._record_usage(provider, usage)
    return raw_text.strip()


async def _translate_full_text(llm_chain: LLMChain, app_config: dict, text: str) -> str:
    chunks = _chunk_text(text)
    translated_parts: list[str] = []
    for chunk in chunks:
        part = await _translate_chunk(llm_chain, app_config, chunk)
        translated_parts.append(part)
    return "\n\n".join(translated_parts)


@router.post("/{paper_id}/translate-full")
async def translate_full_text(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    if not paper.pdf_url:
        raise HTTPException(status_code=400, detail="Paper has no PDF URL")

    if paper.fulltext_cn:
        return {"paper_id": paper.id, "fulltext_cn": paper.fulltext_cn, "cached": True}

    try:
        pdf_text = _extract_pdf_text(paper.pdf_url)
    except Exception as exc:
        logger.exception("Failed to extract PDF text for paper %d", paper_id)
        raise HTTPException(status_code=502, detail=f"Failed to download or parse PDF: {exc}")

    if not pdf_text.strip():
        raise HTTPException(status_code=422, detail="PDF contains no extractable text")

    app_config = await get_app_config(db)
    http_client = httpx.AsyncClient(timeout=120.0)
    llm_chain = LLMChain(db, app_config=app_config, http_client=http_client)
    try:
        fulltext_cn = await _translate_full_text(llm_chain, app_config, pdf_text)
    except Exception as exc:
        logger.exception("Translation failed for paper %d", paper_id)
        raise HTTPException(status_code=502, detail=f"Translation failed: {exc}")
    finally:
        await llm_chain.aclose()

    paper.fulltext_cn = fulltext_cn
    await db.commit()

    return {"paper_id": paper.id, "fulltext_cn": fulltext_cn, "cached": False}


@router.get("/{paper_id}/fulltext")
async def get_fulltext(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    return {
        "paper_id": paper.id,
        "fulltext_cn": paper.fulltext_cn,
        "pdf_url": paper.pdf_url,
    }
