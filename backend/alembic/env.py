import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import DATABASE_URL
from src.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_offline():
    context.configure(url=DATABASE_URL, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
