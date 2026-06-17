import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")

import asyncio

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from httpx import AsyncClient, ASGITransport

from src.models import Base
from src.database import get_db


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(autouse=True)
async def asyncio_thread_wakeup_ticker():
    """Keep the loop waking while aiosqlite posts results from worker threads.

    Some sandboxed WSL/conda environments drop the selector self-pipe wakeup used
    by loop.call_soon_threadsafe after sqlite work in a background thread. A tiny
    ticker gives the loop another scheduled wakeup so queued callbacks run.
    """
    task = asyncio.create_task(_tick_event_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def _tick_event_loop():
    while True:
        await asyncio.sleep(0.001)


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncSession:
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine):
    from src.main import app

    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(client, db_engine):
    from src.models import User
    from src.auth import hash_password, create_access_token

    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=hash_password("testpass"),
        )
        session.add(user)
        await session.commit()

    token = create_access_token("testuser")
    client.cookies.set("session", token)
    return client


@pytest.fixture
def sample_raw():
    from src.core.fetcher import PaperRaw

    def _make(**kwargs):
        defaults = dict(
            title="Test Paper: A Study of Distributed Systems",
            authors=["Alice", "Bob"],
            abstract="This is a test abstract about distributed systems.",
            arxiv_id="2506.12345v1",
            pdf_url="http://arxiv.org/pdf/2506.12345v1",
            url="http://arxiv.org/abs/2506.12345v1",
            comments="Accepted at OSDI'25",
            doi=None,
            published="2025-06-15",
            categories=["cs.DC"],
        )
        defaults.update(kwargs)
        return PaperRaw(**defaults)

    return _make
