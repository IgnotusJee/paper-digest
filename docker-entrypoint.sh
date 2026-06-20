#!/bin/sh
set -e

echo "[entrypoint] Running database migrations..."
alembic upgrade head

echo "[entrypoint] Seeding admin account and default config..."
python scripts/init_db.py

echo "[entrypoint] Starting application server..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000
