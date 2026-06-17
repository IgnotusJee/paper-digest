"""Seed admin account and default system_config. Idempotent."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

from src.models import Base, User, SystemConfig
from src.auth import hash_password
from src.config import DATABASE_URL, ADMIN_USERNAME, ADMIN_EMAIL, ADMIN_PASSWORD, APP_CONFIG


async def main():
    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as db:
        result = await db.execute(select(User).where(User.username == ADMIN_USERNAME))
        if not result.scalar_one_or_none():
            db.add(User(
                username=ADMIN_USERNAME,
                email=ADMIN_EMAIL,
                hashed_password=hash_password(ADMIN_PASSWORD),
            ))
            print(f"[init_db] Created user: {ADMIN_USERNAME}")
        else:
            print(f"[init_db] User '{ADMIN_USERNAME}' already exists, skipping")

        result = await db.execute(select(SystemConfig).where(SystemConfig.key == "app_config"))
        if not result.scalar_one_or_none():
            db.add(SystemConfig(key="app_config", value=json.dumps(APP_CONFIG)))
            print("[init_db] Seeded default app_config")

        await db.commit()

    await engine.dispose()
    print("[init_db] Done")


asyncio.run(main())
