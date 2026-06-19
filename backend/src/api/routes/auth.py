from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...database import get_db
from ...auth import verify_password, create_access_token, check_rate_limit
from ...models import User
from ..deps import get_current_user
from ...config import BASE_URL

router = APIRouter(prefix="/api/auth", tags=["auth"])

_COOKIE = dict(
    key="session",
    httponly=True,
    secure=BASE_URL.startswith("https://"),
    samesite="strict",
    max_age=12 * 3600,
)


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(req: Request, body: LoginRequest, resp: Response, db: AsyncSession = Depends(get_db)):
    ip = req.client.host if req.client else "unknown"
    if not check_rate_limit(ip):
        raise HTTPException(status_code=429, detail="Too many login attempts, try again in 5 minutes")
    result = await db.execute(select(User).where(User.username == body.username, User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    resp.set_cookie(value=create_access_token(user.username), **_COOKIE)
    return {"ok": True}


@router.post("/logout")
async def logout(resp: Response):
    resp.delete_cookie("session")
    return {"ok": True}


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "email": user.email, "daily_total": user.daily_total}
