import pytest
from datetime import date
from unittest.mock import patch, AsyncMock
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.models import DigestHistory, Paper, User
from src.core.dedup import title_hash


class _SessionFactoryWrapper:
    def __init__(self, sf):
        self._sf = sf

    def __call__(self):
        return self._sf()


class TestRunFetchJob:
    @pytest.mark.asyncio
    async def test_new_papers_inserted(self, db_engine):
        from src.core.fetcher import PaperRaw
        from src.core.pipeline import run_fetch_job

        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

        raw = PaperRaw(
            title="New Paper",
            authors=["Author"],
            abstract="Abstract.",
            arxiv_id="2506.00001v1",
            pdf_url="http://arxiv.org/pdf/2506.00001v1",
            url="http://arxiv.org/abs/2506.00001v1",
            comments=None,
            published="2025-06-15",
            categories=["cs.DC"],
        )

        with patch("src.core.pipeline.fetch_arxiv", new_callable=AsyncMock, return_value=[raw]):
            with patch("src.core.pipeline.async_session_factory", _SessionFactoryWrapper(session_factory)):
                stats = await run_fetch_job(date(2025, 6, 15))

        assert stats["fetched"] == 1
        assert stats["new"] == 1
        assert stats["merged"] == 0

        async with session_factory() as session:
            count = (await session.execute(select(func.count(Paper.id)))).scalar()
            assert count == 1

    @pytest.mark.asyncio
    async def test_dedup_merge(self, db_engine):
        from src.core.fetcher import PaperRaw
        from src.core.pipeline import run_fetch_job

        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with session_factory() as session:
            session.add(Paper(
                title="Existing Paper",
                title_hash=title_hash("Existing Paper"),
                source="dblp",
                arxiv_id="2506.00002v1",
                venue="OSDI",
            ))
            await session.commit()

        raw = PaperRaw(
            title="Existing Paper",
            authors=["Author"],
            abstract="Updated abstract from arXiv.",
            arxiv_id="2506.00002v1",
            pdf_url="http://arxiv.org/pdf/2506.00002v1",
            url="http://arxiv.org/abs/2506.00002v1",
            comments="Accepted at OSDI'25",
            published="2025-06-15",
            categories=["cs.DC"],
        )

        with patch("src.core.pipeline.fetch_arxiv", new_callable=AsyncMock, return_value=[raw]):
            with patch("src.core.pipeline.async_session_factory", _SessionFactoryWrapper(session_factory)):
                stats = await run_fetch_job(date(2025, 6, 15))

        assert stats["fetched"] == 1
        assert stats["merged"] == 1
        assert stats["new"] == 0

        async with session_factory() as session:
            count = (await session.execute(select(func.count(Paper.id)))).scalar()
            assert count == 1

            result = await session.execute(select(Paper).where(Paper.arxiv_id == "2506.00002v1"))
            paper = result.scalar_one()
            assert paper.abstract_en == "Updated abstract from arXiv."
            assert paper.venue == "OSDI"

    @pytest.mark.asyncio
    async def test_upsert_failure_counts_errors(self, db_engine):
        from src.core.fetcher import PaperRaw
        from src.core.pipeline import run_fetch_job

        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        raw = PaperRaw(
            title="Broken Paper",
            authors=["Author"],
            abstract="Abstract.",
            arxiv_id="2506.00999v1",
            pdf_url="http://arxiv.org/pdf/2506.00999v1",
            url="http://arxiv.org/abs/2506.00999v1",
            comments=None,
            published="2025-06-15",
            categories=["cs.DC"],
        )

        with patch("src.core.pipeline.fetch_arxiv", new_callable=AsyncMock, return_value=[raw]):
            with patch("src.core.pipeline.find_duplicate", new_callable=AsyncMock) as mock_find:
                mock_find.side_effect = RuntimeError("boom")
                with patch("src.core.pipeline.async_session_factory", _SessionFactoryWrapper(session_factory)):
                    stats = await run_fetch_job(date(2025, 6, 15))

        assert stats["fetched"] == 1
        assert stats["errors"] == 1
        assert "error" not in stats

    @pytest.mark.asyncio
    async def test_upsert_failure_returns_errors_key(self):
        from src.core.fetcher import PaperRaw
        from src.core.pipeline import _upsert_paper

        raw = PaperRaw(
            title="Broken Paper",
            authors=["Author"],
            abstract="Abstract.",
            arxiv_id="2506.00999v1",
            pdf_url="http://arxiv.org/pdf/2506.00999v1",
            url="http://arxiv.org/abs/2506.00999v1",
        )

        with patch("src.core.pipeline.find_duplicate", new_callable=AsyncMock) as mock_find:
            mock_find.side_effect = RuntimeError("boom")
            assert await _upsert_paper(raw, None, "arxiv", db=None) == "errors"

    @pytest.mark.asyncio
    async def test_cross_source_merge_preserves_venue(self, db_engine):
        from src.core.fetcher import PaperRaw
        from src.core.pipeline import run_fetch_job

        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with session_factory() as session:
            session.add(Paper(
                title="Cross Source Paper",
                title_hash=title_hash("Cross Source Paper"),
                source="dblp",
                arxiv_id="2506.00003v1",
                venue="SOSP",
                pushed=True,
            ))
            await session.commit()

        raw = PaperRaw(
            title="Cross Source Paper",
            authors=["Author"],
            abstract="arXiv version abstract.",
            arxiv_id="2506.00003v1",
            pdf_url="http://arxiv.org/pdf/2506.00003v1",
            url="http://arxiv.org/abs/2506.00003v1",
            comments=None,
            published="2025-06-15",
            categories=["cs.DC"],
        )

        with patch("src.core.pipeline.fetch_arxiv", new_callable=AsyncMock, return_value=[raw]):
            with patch("src.core.pipeline.async_session_factory", _SessionFactoryWrapper(session_factory)):
                stats = await run_fetch_job(date(2025, 6, 15))

        assert stats["merged"] == 1

        async with session_factory() as session:
            result = await session.execute(select(Paper).where(Paper.arxiv_id == "2506.00003v1"))
            paper = result.scalar_one()
            assert paper.venue == "SOSP"
            assert paper.bucket == "venue"
            assert paper.pushed is True
            assert paper.abstract_en == "arXiv version abstract."


class TestRunDigestJob:
    @staticmethod
    async def _generate_shortlist(db: AsyncSession):
        result = await db.execute(select(Paper).where(Paper.pushed.is_(False)).order_by(Paper.id))
        return list(result.scalars().all())

    @staticmethod
    async def _run_llm_rank(shortlist, db: AsyncSession, degraded: bool):
        return {
            "papers": shortlist,
            "selected": shortlist,
            "degraded": degraded,
        }

    @pytest.mark.asyncio
    async def test_digest_job_success_marks_papers_and_records_degraded(self, db_engine):
        from src.core.pipeline import run_digest_job

        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with session_factory() as session:
            session.add(User(username="digest", email="digest@example.com", hashed_password="x"))
            session.add(Paper(
                title="Digest Paper",
                title_hash="digestjob000001",
                source="arxiv",
                bucket="arxiv",
                prefilter_score=8.0,
            ))
            await session.commit()

        async def fake_run_llm_rank(shortlist, db):
            return await self._run_llm_rank(shortlist, db, degraded=True)

        with patch("src.core.pipeline.async_session_factory", _SessionFactoryWrapper(session_factory)):
            with patch("src.core.pipeline.run_scoring_job", new_callable=AsyncMock, return_value={"scored": 1}):
                with patch("src.core.pipeline.generate_shortlist", new_callable=AsyncMock, side_effect=self._generate_shortlist):
                    with patch("src.core.pipeline.run_llm_rank", new_callable=AsyncMock, side_effect=fake_run_llm_rank):
                        with patch("src.notifier.EmailNotifier.send_digest", new_callable=AsyncMock, return_value=True):
                            result = await run_digest_job(date(2025, 6, 15))

        assert result["sent"] is True
        assert result["email_status"] == "sent"
        assert result["degraded"] is True

        async with session_factory() as session:
            paper = (await session.execute(select(Paper))).scalar_one()
            assert paper.pushed is True
            assert paper.pushed_at is not None

            history = (await session.execute(select(DigestHistory))).scalar_one()
            assert history.status == "sent"
            assert history.degraded is True
            assert history.paper_ids == [paper.id]
            assert history.bucket_breakdown == {"arxiv": [paper.id]}

    @pytest.mark.asyncio
    async def test_digest_job_failed_email_keeps_papers_unpushed(self, db_engine):
        from src.core.pipeline import run_digest_job

        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with session_factory() as session:
            session.add(User(username="digest", email="digest@example.com", hashed_password="x"))
            session.add(Paper(
                title="Digest Paper",
                title_hash="digestjob000002",
                source="arxiv",
                bucket="arxiv",
                prefilter_score=8.0,
            ))
            await session.commit()

        async def fake_run_llm_rank(shortlist, db):
            return await self._run_llm_rank(shortlist, db, degraded=False)

        with patch("src.core.pipeline.async_session_factory", _SessionFactoryWrapper(session_factory)):
            with patch("src.core.pipeline.run_scoring_job", new_callable=AsyncMock, return_value={"scored": 1}):
                with patch("src.core.pipeline.generate_shortlist", new_callable=AsyncMock, side_effect=self._generate_shortlist):
                    with patch("src.core.pipeline.run_llm_rank", new_callable=AsyncMock, side_effect=fake_run_llm_rank):
                        with patch("src.notifier.EmailNotifier.send_digest", new_callable=AsyncMock, return_value=False):
                            result = await run_digest_job(date(2025, 6, 15))

        assert result["sent"] is False
        assert result["email_status"] == "failed"
        assert result["degraded"] is False

        async with session_factory() as session:
            paper = (await session.execute(select(Paper))).scalar_one()
            assert paper.pushed is False
            assert paper.pushed_at is None

            history = (await session.execute(select(DigestHistory))).scalar_one()
            assert history.status == "failed"
            assert history.degraded is False
            assert history.paper_ids == [paper.id]
            assert history.bucket_breakdown == {"arxiv": [paper.id]}

    @pytest.mark.asyncio
    async def test_digest_job_allows_retry_when_only_failed_history_exists(self, db_engine):
        from src.core.pipeline import run_digest_job

        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with session_factory() as session:
            session.add(User(username="digest", email="digest@example.com", hashed_password="x"))
            session.add(Paper(
                title="Digest Paper",
                title_hash="digestjob000003",
                source="arxiv",
                bucket="arxiv",
                prefilter_score=8.0,
            ))
            session.add(DigestHistory(
                digest_date=date(2025, 6, 15),
                channel="email",
                status="failed",
                degraded=False,
            ))
            await session.commit()

        async def fake_run_llm_rank(shortlist, db):
            return await self._run_llm_rank(shortlist, db, degraded=False)

        with patch("src.core.pipeline.async_session_factory", _SessionFactoryWrapper(session_factory)):
            with patch("src.core.pipeline.run_scoring_job", new_callable=AsyncMock, return_value={"scored": 1}):
                with patch("src.core.pipeline.generate_shortlist", new_callable=AsyncMock, side_effect=self._generate_shortlist):
                    with patch("src.core.pipeline.run_llm_rank", new_callable=AsyncMock, side_effect=fake_run_llm_rank):
                        with patch("src.notifier.EmailNotifier.send_digest", new_callable=AsyncMock, return_value=True):
                            result = await run_digest_job(date(2025, 6, 15))

        assert result["sent"] is True
        assert result["email_status"] == "sent"
        assert result.get("reason") != "already_sent"

        async with session_factory() as session:
            histories = list((await session.execute(select(DigestHistory).order_by(DigestHistory.id))).scalars().all())
            assert len(histories) == 2
            assert [history.status for history in histories] == ["failed", "sent"]

    @pytest.mark.asyncio
    async def test_digest_job_skips_when_success_history_exists(self, db_engine):
        from src.core.pipeline import run_digest_job

        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with session_factory() as session:
            session.add(DigestHistory(
                digest_date=date(2025, 6, 15),
                channel="email",
                status="sent",
                degraded=False,
            ))
            await session.commit()

        with patch("src.core.pipeline.async_session_factory", _SessionFactoryWrapper(session_factory)):
            result = await run_digest_job(date(2025, 6, 15))

        assert result == {"sent": False, "reason": "already_sent"}
