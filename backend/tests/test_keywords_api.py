import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.models import Base, Keyword


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_engine):
    from src.main import app
    from src.database import get_db

    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    from httpx import AsyncClient, ASGITransport
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


class TestAuth:
    @pytest.mark.asyncio
    async def test_unauthenticated_list(self, client):
        resp = await client.get("/api/keywords")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_unauthenticated_create(self, client):
        resp = await client.post("/api/keywords", json={"keyword": "test"})
        assert resp.status_code == 401


class TestGetKeywords:
    @pytest.mark.asyncio
    async def test_empty_list(self, auth_client):
        resp = await auth_client.get("/api/keywords")
        assert resp.status_code == 200
        assert resp.json()["items"] == []
        assert resp.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_list_with_data(self, auth_client, db_engine):
        factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with factory() as session:
            session.add(Keyword(keyword="LLM", weight=1.0, category="topic"))
            session.add(Keyword(keyword="inference", weight=0.8, category="system"))
            await session.commit()

        resp = await auth_client.get("/api/keywords")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    @pytest.mark.asyncio
    async def test_filter_by_category(self, auth_client, db_engine):
        factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with factory() as session:
            session.add(Keyword(keyword="LLM", weight=1.0, category="topic"))
            session.add(Keyword(keyword="inference", weight=0.8, category="system"))
            await session.commit()

        resp = await auth_client.get("/api/keywords?category=system")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["keyword"] == "inference"


class TestCreateKeyword:
    @pytest.mark.asyncio
    async def test_create(self, auth_client):
        resp = await auth_client.post("/api/keywords", json={
            "keyword": "LLM", "weight": 1.0, "category": "topic", "aliases": ["large language model"]
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["keyword"] == "LLM"
        assert data["weight"] == 1.0
        assert data["aliases"] == ["large language model"]

    @pytest.mark.asyncio
    async def test_duplicate(self, auth_client):
        await auth_client.post("/api/keywords", json={"keyword": "LLM"})
        resp = await auth_client.post("/api/keywords", json={"keyword": "LLM"})
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_empty_keyword(self, auth_client):
        resp = await auth_client.post("/api/keywords", json={"keyword": ""})
        assert resp.status_code == 400


class TestUpdateKeyword:
    @pytest.mark.asyncio
    async def test_update(self, auth_client, db_engine):
        factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with factory() as session:
            kw = Keyword(keyword="LLM", weight=1.0, category="topic")
            session.add(kw)
            await session.commit()
            await session.refresh(kw)
            kw_id = kw.id

        resp = await auth_client.put(f"/api/keywords/{kw_id}", json={"weight": 2.0})
        assert resp.status_code == 200
        assert resp.json()["weight"] == 2.0

    @pytest.mark.asyncio
    async def test_not_found(self, auth_client):
        resp = await auth_client.put("/api/keywords/999", json={"weight": 1.0})
        assert resp.status_code == 404


class TestDeleteKeyword:
    @pytest.mark.asyncio
    async def test_delete(self, auth_client, db_engine):
        factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with factory() as session:
            kw = Keyword(keyword="LLM", weight=1.0)
            session.add(kw)
            await session.commit()
            await session.refresh(kw)
            kw_id = kw.id

        resp = await auth_client.delete(f"/api/keywords/{kw_id}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_not_found(self, auth_client):
        resp = await auth_client.delete("/api/keywords/999")
        assert resp.status_code == 404


class TestLoadPreset:
    @pytest.mark.asyncio
    async def test_load_preset(self, auth_client):
        resp = await auth_client.post("/api/keywords/preset", json={"name": "llm_infra"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["loaded"] > 0
        assert data["preset"] == "llm_infra"

    @pytest.mark.asyncio
    async def test_preset_not_found(self, auth_client):
        resp = await auth_client.post("/api/keywords/preset", json={"name": "nonexistent"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_preset_idempotent(self, auth_client):
        await auth_client.post("/api/keywords/preset", json={"name": "llm_infra"})
        resp = await auth_client.post("/api/keywords/preset", json={"name": "llm_infra"})
        assert resp.status_code == 200
        assert resp.json()["loaded"] == 0
        assert resp.json()["skipped"] > 0
