from html import escape

from fastapi import APIRouter, Depends, Form, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models import Paper, Tag
from ...auth import verify_feedback_token
from ..deps import get_current_user

router = APIRouter(prefix="/api/papers", tags=["feedback"])

_TAG_TYPES = {"interested", "not_interested", "read_later"}

_CONFIRM_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{{font-family:sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;background:#f4f6fb;padding:24px;box-sizing:border-box}}
.box{{max-width:520px;width:100%;padding:32px;background:#fff;border-radius:16px;box-shadow:0 10px 30px rgba(15,23,42,.08);text-align:center}}
.eyebrow{{font-size:13px;color:#64748b;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px}}
h1{{font-size:28px;margin:0 0 12px;color:#0f172a}}
p{{margin:0 0 10px;color:#475569;line-height:1.6}}
form{{margin-top:24px}}
button{{border:0;border-radius:999px;background:#0f172a;color:#fff;padding:12px 22px;font-size:15px;cursor:pointer}}
</style></head>
<body><div class="box"><div class="eyebrow">Paper Digest Feedback</div><h1>确认标记为“{tag_label}”</h1><p>{paper_title}</p><p>确认后才会记录到系统。</p><form method="post" action="/api/papers/{paper_id}/feedback"><input type="hidden" name="t" value="{token}"><input type="hidden" name="action" value="{action}"><button type="submit">确认提交</button></form></div></body></html>"""

_SUCCESS_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{{font-family:sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;background:#f4f6fb;padding:24px;box-sizing:border-box}}
.box{{max-width:520px;width:100%;padding:32px;background:#fff;border-radius:16px;box-shadow:0 10px 30px rgba(15,23,42,.08);text-align:center}}
.icon{{font-size:40px;margin-bottom:12px}}
h1{{font-size:28px;margin:0 0 12px;color:#0f172a}}
p{{margin:0;color:#475569;line-height:1.6}}
</style></head>
<body><div class="box"><div class="icon">✓</div><h1>已记录为“{tag_label}”</h1><p>{paper_title}</p><p>可以关闭此页面。</p></div></body></html>"""

_TAG_LABELS = {
    "interested": "感兴趣",
    "not_interested": "不感兴趣",
    "read_later": "稍后读",
}


class TagRequest(BaseModel):
    tag_type: str


async def _verify_feedback_request(
    paper_id: int,
    db: AsyncSession,
    *,
    t: str,
    action: str,
) -> Paper:
    result = verify_feedback_token(t)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    token_paper_id, token_action = result
    if token_paper_id != paper_id or token_action != action:
        raise HTTPException(status_code=401, detail="Token mismatch")

    if action not in _TAG_TYPES:
        raise HTTPException(status_code=400, detail="Invalid action")

    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    return paper


async def _replace_tag(db: AsyncSession, paper_id: int, action: str) -> None:
    await db.execute(delete(Tag).where(Tag.paper_id == paper_id))
    db.add(Tag(paper_id=paper_id, tag_type=action))
    await db.commit()


def _render_confirm_page(paper: Paper, paper_id: int, token: str, action: str) -> str:
    label = _TAG_LABELS.get(action, action)
    return _CONFIRM_HTML.format(
        tag_label=escape(label),
        paper_title=escape(paper.title),
        paper_id=paper_id,
        token=escape(token, quote=True),
        action=escape(action, quote=True),
    )


def _render_success_page(paper: Paper, action: str) -> str:
    label = _TAG_LABELS.get(action, action)
    return _SUCCESS_HTML.format(
        tag_label=escape(label),
        paper_title=escape(paper.title),
    )


@router.get("/{paper_id}/feedback")
async def handle_feedback_link(
    paper_id: int,
    t: str = Query(...),
    action: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    paper = await _verify_feedback_request(paper_id, db, t=t, action=action)
    return HTMLResponse(_render_confirm_page(paper, paper_id, t, action))


@router.post("/{paper_id}/feedback")
async def confirm_feedback_link(
    paper_id: int,
    t: str = Form(...),
    action: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    paper = await _verify_feedback_request(paper_id, db, t=t, action=action)
    await _replace_tag(db, paper_id, action)
    return HTMLResponse(_render_success_page(paper, action))


@router.post("/{paper_id}/tag")
async def add_tag(
    paper_id: int,
    body: TagRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    if body.tag_type not in _TAG_TYPES:
        raise HTTPException(status_code=400, detail="Invalid tag_type")

    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    await _replace_tag(db, paper_id, body.tag_type)

    return {"ok": True, "tag_type": body.tag_type}


@router.delete("/{paper_id}/tag")
async def remove_tag(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    await db.execute(delete(Tag).where(Tag.paper_id == paper_id))
    await db.commit()
    return None
