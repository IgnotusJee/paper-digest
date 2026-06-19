import time

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.auth import gen_feedback_token
from src.models import Paper, Tag


async def _tag_count(session, paper_id: int) -> int:
    result = await session.execute(select(func.count(Tag.id)).where(Tag.paper_id == paper_id))
    return int(result.scalar_one())


class TestFeedbackLink:
    @pytest.mark.asyncio
    async def test_feedback_link_get_valid_token_renders_confirm_page_only(self, client, db_engine):
        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with session_factory() as session:
            paper = Paper(title="Test Paper", title_hash="fbtest000000001", source="arxiv")
            session.add(paper)
            await session.commit()
            paper_id = paper.id

        token = gen_feedback_token(paper_id, "interested")
        resp = await client.get(f"/api/papers/{paper_id}/feedback?t={token}&action=interested")
        assert resp.status_code == 200
        assert "确认提交" in resp.text
        assert "感兴趣" in resp.text
        assert 'method="post"' in resp.text

        async with session_factory() as session:
            assert await _tag_count(session, paper_id) == 0

    @pytest.mark.asyncio
    async def test_feedback_link_post_valid_token_creates_tag(self, client, db_engine):
        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with session_factory() as session:
            paper = Paper(title="Test Paper", title_hash="fbtest000000005", source="arxiv")
            session.add(paper)
            await session.commit()
            paper_id = paper.id

        token = gen_feedback_token(paper_id, "interested")
        resp = await client.post(
            f"/api/papers/{paper_id}/feedback",
            data={"t": token, "action": "interested"},
        )
        assert resp.status_code == 200
        assert "已记录为" in resp.text
        assert "感兴趣" in resp.text

        async with session_factory() as session:
            result = await session.execute(select(Tag).where(Tag.paper_id == paper_id))
            tags = list(result.scalars().all())
            assert len(tags) == 1
            assert tags[0].tag_type == "interested"

    @pytest.mark.asyncio
    async def test_feedback_link_post_replaces_existing_and_is_idempotent(self, client, db_engine):
        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with session_factory() as session:
            paper = Paper(title="Test Paper", title_hash="fbtest000000006", source="arxiv")
            session.add(paper)
            await session.commit()
            paper_id = paper.id

        interested_token = gen_feedback_token(paper_id, "interested")
        not_interested_token = gen_feedback_token(paper_id, "not_interested")

        resp1 = await client.post(
            f"/api/papers/{paper_id}/feedback",
            data={"t": interested_token, "action": "interested"},
        )
        assert resp1.status_code == 200

        resp2 = await client.post(
            f"/api/papers/{paper_id}/feedback",
            data={"t": not_interested_token, "action": "not_interested"},
        )
        assert resp2.status_code == 200

        resp3 = await client.post(
            f"/api/papers/{paper_id}/feedback",
            data={"t": not_interested_token, "action": "not_interested"},
        )
        assert resp3.status_code == 200

        async with session_factory() as session:
            result = await session.execute(select(Tag).where(Tag.paper_id == paper_id))
            tags = list(result.scalars().all())
            assert len(tags) == 1
            assert tags[0].tag_type == "not_interested"

    @pytest.mark.asyncio
    async def test_feedback_link_expired_token_rejected_for_get_and_post(self, client, db_engine):
        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with session_factory() as session:
            paper = Paper(title="Test Paper", title_hash="fbtest000000002", source="arxiv")
            session.add(paper)
            await session.commit()
            paper_id = paper.id

        exp = int(time.time()) - 3600
        payload = f"{paper_id}:interested:{exp}"
        import hashlib
        import hmac
        from src.config import JWT_SECRET

        sig = hmac.new(JWT_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
        token = f"{paper_id}:interested:{exp}:{sig}"

        get_resp = await client.get(f"/api/papers/{paper_id}/feedback?t={token}&action=interested")
        assert get_resp.status_code == 401

        post_resp = await client.post(
            f"/api/papers/{paper_id}/feedback",
            data={"t": token, "action": "interested"},
        )
        assert post_resp.status_code == 401

    @pytest.mark.asyncio
    async def test_feedback_link_mismatched_paper_rejected_for_get_and_post(self, client, db_engine):
        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with session_factory() as session:
            paper = Paper(title="Test Paper", title_hash="fbtest000000003", source="arxiv")
            session.add(paper)
            await session.commit()
            paper_id = paper.id

        token = gen_feedback_token(paper_id, "interested")
        get_resp = await client.get(f"/api/papers/99999/feedback?t={token}&action=interested")
        assert get_resp.status_code == 401

        post_resp = await client.post(
            "/api/papers/99999/feedback",
            data={"t": token, "action": "interested"},
        )
        assert post_resp.status_code == 401

    @pytest.mark.asyncio
    async def test_feedback_link_mismatched_action_rejected_for_get_and_post(self, client, db_engine):
        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with session_factory() as session:
            paper = Paper(title="Test Paper", title_hash="fbtest000000004", source="arxiv")
            session.add(paper)
            await session.commit()
            paper_id = paper.id

        token = gen_feedback_token(paper_id, "interested")
        get_resp = await client.get(f"/api/papers/{paper_id}/feedback?t={token}&action=not_interested")
        assert get_resp.status_code == 401

        post_resp = await client.post(
            f"/api/papers/{paper_id}/feedback",
            data={"t": token, "action": "not_interested"},
        )
        assert post_resp.status_code == 401


class TestTagAPI:
    @pytest.mark.asyncio
    async def test_add_tag_logged_in(self, auth_client, db_engine):
        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with session_factory() as session:
            paper = Paper(title="Test Paper", title_hash="tagtest00000001", source="arxiv")
            session.add(paper)
            await session.commit()
            paper_id = paper.id

        resp = await auth_client.post(
            f"/api/papers/{paper_id}/tag",
            json={"tag_type": "interested"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["tag_type"] == "interested"

    @pytest.mark.asyncio
    async def test_add_tag_replaces_existing(self, auth_client, db_engine):
        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with session_factory() as session:
            paper = Paper(title="Test Paper", title_hash="tagtest00000002", source="arxiv")
            session.add(paper)
            await session.commit()
            paper_id = paper.id

        resp1 = await auth_client.post(
            f"/api/papers/{paper_id}/tag",
            json={"tag_type": "interested"},
        )
        assert resp1.status_code == 200

        resp2 = await auth_client.post(
            f"/api/papers/{paper_id}/tag",
            json={"tag_type": "not_interested"},
        )
        assert resp2.status_code == 200

        async with session_factory() as session:
            result = await session.execute(select(Tag).where(Tag.paper_id == paper_id))
            tags = list(result.scalars().all())
            assert len(tags) == 1
            assert tags[0].tag_type == "not_interested"

    @pytest.mark.asyncio
    async def test_remove_tag(self, auth_client, db_engine):
        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with session_factory() as session:
            paper = Paper(title="Test Paper", title_hash="tagtest00000003", source="arxiv")
            session.add(paper)
            await session.commit()
            paper_id = paper.id

        await auth_client.post(
            f"/api/papers/{paper_id}/tag",
            json={"tag_type": "interested"},
        )

        resp = await auth_client.delete(f"/api/papers/{paper_id}/tag")
        assert resp.status_code == 200

        async with session_factory() as session:
            result = await session.execute(select(Tag).where(Tag.paper_id == paper_id))
            tags = list(result.scalars().all())
            assert len(tags) == 0

    @pytest.mark.asyncio
    async def test_add_tag_no_auth(self, client, db_engine):
        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with session_factory() as session:
            paper = Paper(title="Test Paper", title_hash="tagtest00000004", source="arxiv")
            session.add(paper)
            await session.commit()
            paper_id = paper.id

        resp = await client.post(
            f"/api/papers/{paper_id}/tag",
            json={"tag_type": "interested"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_add_tag_invalid_type(self, auth_client, db_engine):
        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with session_factory() as session:
            paper = Paper(title="Test Paper", title_hash="tagtest00000005", source="arxiv")
            session.add(paper)
            await session.commit()
            paper_id = paper.id

        resp = await auth_client.post(
            f"/api/papers/{paper_id}/tag",
            json={"tag_type": "invalid"},
        )
        assert resp.status_code == 400
