"""Seed keyword presets into database. Idempotent."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.models import Keyword
from src.config import DATABASE_URL


PRESETS_DIR = Path(__file__).parent.parent / "config" / "presets"


async def seed_preset(preset_name: str, db_session_factory):
    preset_path = PRESETS_DIR / f"{preset_name}.json"
    if not preset_path.exists():
        print(f"[seed_keywords] Preset not found: {preset_path}")
        return

    with open(preset_path) as f:
        items = json.load(f)

    loaded = 0
    skipped = 0
    async with db_session_factory() as db:
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

    print(f"[seed_keywords] Preset '{preset_name}': loaded={loaded}, skipped={skipped}")


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Seed keyword presets")
    parser.add_argument("--preset", default="llm_infra", help="Preset name (default: llm_infra)")
    args = parser.parse_args()

    engine = create_async_engine(DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    await seed_preset(args.preset, Session)

    await engine.dispose()
    print("[seed_keywords] Done")


if __name__ == "__main__":
    asyncio.run(main())
