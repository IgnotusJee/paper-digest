import pytest
from datetime import date, datetime
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.models import Paper, DigestHistory


class TestGetDigest:
    @pytest.mark.asyncio
    async def test_get_today_digest_empty(self, auth_client):
        resp = await auth_client.get("/api/digest")
        assert resp.status_code == 404
        assert "No digest" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_digest_by_date(self, auth_client, db_engine):
        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with session_factory() as session:
            paper = Paper(
                title="Digest Paper",
                title_hash="digesttest00001",
                source="arxiv",
                bucket="arxiv",
                final_score=8.5,
                pushed=True,
            )
            session.add(paper)
            await session.flush()

            failed_record = DigestHistory(
                digest_date=date(2025, 6, 15),
                paper_ids=None,
                bucket_breakdown=None,
                channel="email",
                status="failed",
                degraded=False,
                created_at=datetime(2025, 6, 15, 8, 0, 0),
            )
            sent_record = DigestHistory(
                digest_date=date(2025, 6, 15),
                paper_ids=[paper.id],
                bucket_breakdown={"arxiv": [paper.id]},
                channel="email",
                status="sent",
                degraded=True,
                created_at=datetime(2025, 6, 15, 9, 0, 0),
            )
            session.add_all([failed_record, sent_record])
            await session.commit()

        resp = await auth_client.get("/api/digest/2025-06-15")
        assert resp.status_code == 200
        data = resp.json()
        assert data["date"] == "2025-06-15"
        assert len(data["papers"]) == 1
        assert data["papers"][0]["title"] == "Digest Paper"
        assert data["status"] == "sent"
        assert data["degraded"] is True
        assert data["channel"] == "email"

    @pytest.mark.asyncio
    async def test_get_digest_invalid_date(self, auth_client):
        resp = await auth_client.get("/api/digest/not-a-date")
        assert resp.status_code == 400
        assert "Invalid date" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_digest_no_auth(self, client):
        resp = await client.get("/api/digest")
        assert resp.status_code == 401
