from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..auth import decode_token
from ..models import User


async def get_current_user(
    session: str = Cookie(default=None, alias="session"),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    username = decode_token(session)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    result = await db.execute(select(User).where(User.username == username, User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
