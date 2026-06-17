import pytest


class TestListPapers:
    @pytest.mark.asyncio
    async def test_empty(self, auth_client):
        resp = await auth_client.get("/api/papers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_unauthorized(self, client):
        resp = await client.get("/api/papers")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_list_with_data(self, auth_client, db_engine):
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from src.models import Paper

        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with session_factory() as session:
            for i in range(3):
                session.add(Paper(
                    title=f"Paper {i}",
                    title_hash=f"hash{i:013d}",
                    source="arxiv",
                    bucket="arxiv",
                ))
            await session.commit()

        resp = await auth_client.get("/api/papers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    @pytest.mark.asyncio
    async def test_pagination(self, auth_client, db_engine):
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from src.models import Paper

        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with session_factory() as session:
            for i in range(25):
                session.add(Paper(
                    title=f"Paper {i}",
                    title_hash=f"p{i:014d}",
                    source="arxiv",
                    bucket="arxiv",
                ))
            await session.commit()

        resp = await auth_client.get("/api/papers?page=2&size=10")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 10
        assert data["page"] == 2
        assert data["total"] == 25
        assert data["pages"] == 3

    @pytest.mark.asyncio
    async def test_filter_bucket(self, auth_client, db_engine):
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from src.models import Paper

        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with session_factory() as session:
            session.add(Paper(title="Venue", title_hash="venue0000000000", source="dblp", bucket="venue"))
            session.add(Paper(title="Arxiv", title_hash="arxiv0000000000", source="arxiv", bucket="arxiv"))
            await session.commit()

        resp = await auth_client.get("/api/papers?bucket=venue")
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Venue"


class TestGetPaper:
    @pytest.mark.asyncio
    async def test_get_existing(self, auth_client, db_engine):
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from src.models import Paper

        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with session_factory() as session:
            paper = Paper(
                title="Test Paper",
                title_hash="testhash1234567",
                source="arxiv",
                abstract_en="Abstract text",
            )
            session.add(paper)
            await session.commit()
            paper_id = paper.id

        resp = await auth_client.get(f"/api/papers/{paper_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Test Paper"
        assert data["abstract_en"] == "Abstract text"

    @pytest.mark.asyncio
    async def test_get_not_found(self, auth_client):
        resp = await auth_client.get("/api/papers/99999")
        assert resp.status_code == 404
