import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.models import Base, Paper, Tag, User
from src.core.recommender import get_mode, score, mark_dirty, retrain_if_dirty


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


async def _make_paper(db, idx=1, abstract="Test abstract about distributed systems"):
    paper = Paper(
        title=f"Test Paper {idx}",
        title_hash=f"hash{idx:012d}",
        authors=["Author"],
        abstract_en=abstract,
        source="arxiv",
    )
    db.add(paper)
    await db.commit()
    await db.refresh(paper)
    return paper


async def _tag_paper(db, paper_id, tag_type):
    tag = Tag(paper_id=paper_id, tag_type=tag_type)
    db.add(tag)
    await db.commit()


class TestOffMode:
    @pytest.mark.asyncio
    async def test_mode_is_off(self, db_session):
        mode = await get_mode(db_session)
        assert mode == "off"

    @pytest.mark.asyncio
    async def test_returns_half(self, db_session):
        paper = await _make_paper(db_session)
        result = await score(paper, db_session)
        assert result == 0.5


class TestCentroidMode:
    @pytest.mark.asyncio
    async def test_activates_with_one_positive(self, db_session):
        paper = await _make_paper(db_session, 1)
        await _tag_paper(db_session, paper.id, "interested")
        mark_dirty()
        mode = await get_mode(db_session)
        assert mode == "centroid"

    @pytest.mark.asyncio
    async def test_returns_similarity(self, db_session):
        paper1 = await _make_paper(db_session, 1, "Distributed systems and consensus protocols")
        await _tag_paper(db_session, paper1.id, "interested")
        mark_dirty()

        paper2 = await _make_paper(db_session, 2, "Distributed consensus in blockchain systems")
        result = await score(paper2, db_session)
        assert result != 0.5
        assert 0.0 <= result <= 1.0


class TestModelMode:
    @pytest.mark.asyncio
    async def test_activates_with_sufficient_samples(self, db_session):
        papers_pos = []
        for i in range(21):
            p = await _make_paper(db_session, i + 1, f"Positive abstract {i} about LLM inference")
            await _tag_paper(db_session, p.id, "interested")
            papers_pos.append(p)

        for i in range(21):
            p = await _make_paper(db_session, i + 100, f"Negative abstract {i} about quantum computing")
            await _tag_paper(db_session, p.id, "not_interested")

        mark_dirty()
        mode = await get_mode(db_session)
        assert mode == "model"


class TestDirtyFlag:
    @pytest.mark.asyncio
    async def test_dirty_triggers_retrain(self, db_session):
        mark_dirty()
        paper = await _make_paper(db_session)
        await _tag_paper(db_session, paper.id, "interested")
        mark_dirty()

        result = await score(paper, db_session)
        assert 0.0 <= result <= 1.0
