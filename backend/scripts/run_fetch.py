"""Manual fetch trigger. Usage: python scripts/run_fetch.py [--date YYYY-MM-DD]"""
import asyncio
import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.pipeline import run_fetch_job


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=date.fromisoformat, default=None)
    args = parser.parse_args()
    stats = await run_fetch_job(args.date)
    print(f"[run_fetch] Done: {stats}")


if __name__ == "__main__":
    asyncio.run(main())
