from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import get_app_config, save_app_config, validate_app_config
from ...database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
async def get_settings(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await get_app_config(db)


@router.put("")
async def put_settings(
    body: dict,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        validate_app_config(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return await save_app_config(db, body)
