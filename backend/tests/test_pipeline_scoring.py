import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.models import Base, Paper, Keyword
from src.core.pipeline import assign_bucket, run_scoring_job, generate_shortlist


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
async def db_session(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


class TestAssignBucket:
    def test_venue_match(self, monkeypatch):
        monkeypatch.setattr("src.core.pipeline.APP_CONFIG", {
            "sources": {"buckets": [
                {"name": "venue", "venues": ["FAST", "OSDI"], "include_venue_hint": True},
                {"name": "arxiv"},
            ]}
        })
        assert assign_bucket("FAST", None) == "venue"

    def test_venue_hint(self, monkeypatch):
        monkeypatch.setattr("src.core.pipeline.APP_CONFIG", {
            "sources": {"buckets": [
                {"name": "venue", "venues": ["FAST"], "include_venue_hint": True},
                {"name": "arxiv"},
            ]}
        })
        assert assign_bucket(None, "OSDI") == "venue"

    def test_pure_arxiv(self, monkeypatch):
        monkeypatch.setattr("src.core.pipeline.APP_CONFIG", {
            "sources": {"buckets": [
                {"name": "venue", "venues": ["FAST"], "include_venue_hint": True},
                {"name": "arxiv"},
            ]}
        })
        assert assign_bucket(None, None) == "arxiv"

    def test_venue_hint_disabled(self, monkeypatch):
        monkeypatch.setattr("src.core.pipeline.APP_CONFIG", {
            "sources": {"buckets": [
                {"name": "venue", "venues": ["FAST"], "include_venue_hint": False},
                {"name": "arxiv"},
            ]}
        })
        assert assign_bucket(None, "OSDI") == "arxiv"


class TestScoringJob:
    @pytest.mark.asyncio
    async def test_scores_papers(self, db_session, monkeypatch):
        monkeypatch.setattr("src.core.pipeline.APP_CONFIG", {
            "sources": {"buckets": [{"name": "venue", "venues": ["FAST"]}, {"name": "arxiv"}]},
            "scoring": {"prefilter": {"keyword": 0.45, "personal": 0.30, "recency": 0.15, "source_prior": 0.10}},
            "recommender": {"min_pos_centroid": 1, "min_pos_model": 20, "min_neg_model": 20},
        })
        monkeypatch.setattr("src.core.scorer.APP_CONFIG", {
            "sources": {"buckets": [{"name": "venue", "venues": ["FAST"]}]},
            "scoring": {"prefilter": {"keyword": 0.45, "personal": 0.30, "recency": 0.15, "source_prior": 0.10}},
        })

        db_session.add(Keyword(keyword="distributed", weight=1.0, category="topic"))
        paper = Paper(
            title="Distributed Systems Study",
            title_hash="testhash000001",
            authors=["Author"],
            abstract_en="A study of distributed systems",
            source="arxiv",
            bucket="arxiv",
        )
        db_session.add(paper)
        await db_session.commit()

        result = await run_scoring_job(db_session)
        assert result["scored"] == 1

        await db_session.refresh(paper)
        assert paper.keyword_score > 0.0
        assert paper.prefilter_score > 0.0
        assert 0.0 <= paper.personal_score <= 1.0

    @pytest.mark.asyncio
    async def test_scoring_assigns_bucket_before_shortlist(self, db_session, monkeypatch):
        monkeypatch.setattr("src.core.pipeline.APP_CONFIG", {
            "sources": {
                "buckets": [
                    {"name": "venue", "venues": ["FAST"], "quota": 3, "enabled": True},
                    {"name": "arxiv", "quota": 3, "enabled": True},
                ],
                "oversample": 3,
            },
            "scoring": {"prefilter": {"keyword": 0.45, "personal": 0.30, "recency": 0.15, "source_prior": 0.10}},
            "recommender": {"min_pos_centroid": 1, "min_pos_model": 20, "min_neg_model": 20},
        })
        monkeypatch.setattr("src.core.scorer.APP_CONFIG", {
            "sources": {"buckets": [{"name": "venue", "venues": ["FAST"]}]},
            "scoring": {"prefilter": {"keyword": 0.45, "personal": 0.30, "recency": 0.15, "source_prior": 0.10}},
        })

        paper = Paper(
            title="FAST Systems Study",
            title_hash="fastbucket00001",
            authors=["Author"],
            abstract_en="A study of storage systems",
            source="manual",
            venue="FAST",
            bucket=None,
            prefilter_score=0.0,
        )
        db_session.add(paper)
        await db_session.commit()

        result = await run_scoring_job(db_session)
        assert result["scored"] == 1

        await db_session.refresh(paper)
        assert paper.bucket == "venue"

        shortlist = await generate_shortlist(db_session)
        assert paper.id in {p.id for p in shortlist}


class TestShortlist:
    @pytest.mark.asyncio
    async def test_shortlist_respects_quota(self, db_session, monkeypatch):
        monkeypatch.setattr("src.core.pipeline.APP_CONFIG", {
            "sources": {
                "buckets": [
                    {"name": "venue", "quota": 3, "enabled": True},
                    {"name": "arxiv", "quota": 3, "enabled": True},
                ],
                "oversample": 3,
            },
        })

        for i in range(15):
            db_session.add(Paper(
                title=f"Venue Paper {i}",
                title_hash=f"venue{i:012d}",
                source="arxiv",
                bucket="venue",
                prefilter_score=float(15 - i),
            ))
        for i in range(15):
            db_session.add(Paper(
                title=f"Arxiv Paper {i}",
                title_hash=f"arxiv{i:012d}",
                source="arxiv",
                bucket="arxiv",
                prefilter_score=float(15 - i),
            ))
        await db_session.commit()

        shortlist = await generate_shortlist(db_session)
        assert len(shortlist) <= 18
        venue_count = sum(1 for p in shortlist if p.bucket == "venue")
        arxiv_count = sum(1 for p in shortlist if p.bucket == "arxiv")
        assert venue_count <= 9
        assert arxiv_count <= 9

    @pytest.mark.asyncio
    async def test_shortlist_sorted_by_score(self, db_session, monkeypatch):
        monkeypatch.setattr("src.core.pipeline.APP_CONFIG", {
            "sources": {
                "buckets": [
                    {"name": "venue", "quota": 2, "enabled": True},
                    {"name": "arxiv", "quota": 2, "enabled": True},
                ],
                "oversample": 2,
            },
        })

        for i in range(5):
            db_session.add(Paper(
                title=f"Paper {i}",
                title_hash=f"sort{i:012d}",
                source="arxiv",
                bucket="arxiv",
                prefilter_score=float(5 - i),
            ))
        await db_session.commit()

        shortlist = await generate_shortlist(db_session)
        arxiv_papers = [p for p in shortlist if p.bucket == "arxiv"]
        scores = [p.prefilter_score for p in arxiv_papers]
        assert scores == sorted(scores, reverse=True)
