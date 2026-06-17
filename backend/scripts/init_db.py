"""Seed admin account and default system_config. Idempotent."""
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

from src.models import User, SystemConfig
from src.auth import hash_password
from src.config import DATABASE_URL, APP_CONFIG


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"[init_db] Missing required environment variable: {name}")
    return value


async def main():
    admin_username = os.environ.get("ADMIN_USERNAME", "admin")
    admin_email = require_env("ADMIN_EMAIL")
    admin_password = require_env("ADMIN_PASSWORD")

    engine = create_async_engine(DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as db:
        result = await db.execute(select(User).where(User.username == admin_username))
        if not result.scalar_one_or_none():
            db.add(User(
                username=admin_username,
                email=admin_email,
                hashed_password=hash_password(admin_password),
            ))
            print(f"[init_db] Created user: {admin_username}")
        else:
            print(f"[init_db] User '{admin_username}' already exists, skipping")

        result = await db.execute(select(SystemConfig).where(SystemConfig.key == "app_config"))
        if not result.scalar_one_or_none():
            db.add(SystemConfig(key="app_config", value=json.dumps(APP_CONFIG)))
            print("[init_db] Seeded default app_config")

        await db.commit()

    await engine.dispose()
    print("[init_db] Done")


asyncio.run(main())
