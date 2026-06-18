import copy
import json

import httpx
import pytest

from src.config import merge_app_config
from src.core.llm_client import LLMChain, LLMUnavailable
from src.core.pipeline import run_llm_rank
from src.models import Paper, SystemConfig


async def _set_app_config(db_session, config: dict):
    payload = json.dumps(config)
    existing = await db_session.get(SystemConfig, "app_config")
    if existing:
        existing.value = payload
    else:
        db_session.add(SystemConfig(key="app_config", value=payload))
    await db_session.commit()


async def _make_papers(db_session, venue_count: int, arxiv_count: int) -> list[Paper]:
    papers: list[Paper] = []
    index = 0
    for bucket, count in (("venue", venue_count), ("arxiv", arxiv_count)):
        for _ in range(count):
            paper = Paper(
                title=f"{bucket.title()} Paper {index}",
                title_hash=f"{bucket[:2]}{index:014d}",
                source="arxiv",
                bucket=bucket,
                prefilter_score=float(100 - index),
            )
            db_session.add(paper)
            papers.append(paper)
            index += 1
    await db_session.commit()
    for paper in papers:
        await db_session.refresh(paper)
    return papers


class StubLLMChain:
    def __init__(self, score_map: dict[int, float]):
        self.score_map = score_map

    async def chat_json(self, messages, schema, validator=None):
        payload = json.loads(messages[1]["content"])
        data = {
            "papers": [
                {
                    "id": item["id"],
                    "relevance": self.score_map[item["id"]],
                    "reason": f"reason-{item['id']}",
                }
                for item in payload["papers"]
            ]
        }
        if validator:
            validator(data)
        return data

    async def aclose(self):
        return None


def _set_provider_env(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://deepseek.test/v1")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-chat")
    monkeypatch.setenv("KIMI_API_KEY", "kimi-key")
    monkeypatch.setenv("KIMI_BASE_URL", "https://kimi.test/v1")
    monkeypatch.setenv("KIMI_MODEL", "moonshot-v1-8k")


class TestPipelineLLM:
    @pytest.mark.asyncio
    async def test_run_llm_rank_writes_scores(self, db_session):
        config = copy.deepcopy(merge_app_config())
        config["sources"]["fill_policy"] = "strict"
        config["sources"]["daily_total"] = 6
        config["sources"]["buckets"][0]["quota"] = 3
        config["sources"]["buckets"][1]["quota"] = 3
        config["llm"]["batch_size"] = 4
        await _set_app_config(db_session, config)

        shortlist = await _make_papers(db_session, venue_count=6, arxiv_count=6)
        score_map = {paper.id: float(200 - idx) / 10.0 for idx, paper in enumerate(shortlist)}

        result = await run_llm_rank(shortlist, db_session, llm_chain=StubLLMChain(score_map))

        assert result["degraded"] is False
        assert len(result["papers"]) == 6
        for paper in shortlist:
            await db_session.refresh(paper)
            assert paper.llm_score == score_map[paper.id]
            assert paper.llm_reason == f"reason-{paper.id}"
            assert paper.final_score == score_map[paper.id]

    @pytest.mark.asyncio
    async def test_fill_policy_strict_does_not_spill(self, db_session):
        config = copy.deepcopy(merge_app_config())
        config["sources"]["fill_policy"] = "strict"
        config["sources"]["daily_total"] = 4
        config["sources"]["buckets"][0]["quota"] = 2
        config["sources"]["buckets"][1]["quota"] = 2
        await _set_app_config(db_session, config)

        shortlist = await _make_papers(db_session, venue_count=1, arxiv_count=5)
        score_map = {paper.id: float(100 - idx) / 10.0 for idx, paper in enumerate(shortlist)}

        result = await run_llm_rank(shortlist, db_session, llm_chain=StubLLMChain(score_map))

        assert result["degraded"] is False
        assert len(result["papers"]) == 3
        assert sum(1 for paper in result["papers"] if paper.bucket == "venue") == 1
        assert sum(1 for paper in result["papers"] if paper.bucket == "arxiv") == 2

    @pytest.mark.asyncio
    async def test_fill_policy_spillover_fills_total(self, db_session):
        config = copy.deepcopy(merge_app_config())
        config["sources"]["fill_policy"] = "spillover"
        config["sources"]["daily_total"] = 4
        config["sources"]["buckets"][0]["quota"] = 2
        config["sources"]["buckets"][1]["quota"] = 2
        await _set_app_config(db_session, config)

        shortlist = await _make_papers(db_session, venue_count=1, arxiv_count=5)
        score_map = {paper.id: float(100 - idx) / 10.0 for idx, paper in enumerate(shortlist)}

        result = await run_llm_rank(shortlist, db_session, llm_chain=StubLLMChain(score_map))

        assert result["degraded"] is False
        assert len(result["papers"]) == 4
        assert sum(1 for paper in result["papers"] if paper.bucket == "venue") == 1
        assert sum(1 for paper in result["papers"] if paper.bucket == "arxiv") == 3

    @pytest.mark.asyncio
    async def test_degrades_to_prefilter_when_budget_exceeded(self, db_session, monkeypatch):
        _set_provider_env(monkeypatch)
        config = copy.deepcopy(merge_app_config())
        config["llm"]["chain"] = ["deepseek"]
        config["llm"]["daily_budget"] = 0.000001
        await _set_app_config(db_session, config)

        shortlist = await _make_papers(db_session, venue_count=3, arxiv_count=3)
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    status_code=200,
                    json={
                        "choices": [{"message": {"content": '{"papers":[{"id":1,"relevance":9,"reason":"x"}]}'}}],
                        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
                    },
                )
            )
        )
        chain = LLMChain(db_session, app_config=config, http_client=client)
        try:
            result = await run_llm_rank(shortlist, db_session, llm_chain=chain)
        finally:
            await chain.aclose()

        assert result["degraded"] is True
        for paper in shortlist:
            await db_session.refresh(paper)
            assert paper.llm_score is None
            assert paper.final_score == paper.prefilter_score

    @pytest.mark.asyncio
    async def test_falls_back_to_next_provider(self, db_session, monkeypatch):
        _set_provider_env(monkeypatch)
        config = copy.deepcopy(merge_app_config())
        config["llm"]["chain"] = ["deepseek", "kimi"]
        await _set_app_config(db_session, config)

        shortlist = await _make_papers(db_session, venue_count=1, arxiv_count=1)

        def handler(request):
            if request.url.host == "deepseek.test":
                return httpx.Response(status_code=500, json={"error": "boom"})
            payload = json.loads(request.content.decode("utf-8"))
            paper_ids = [item["id"] for item in json.loads(payload["messages"][1]["content"])["papers"]]
            return httpx.Response(
                status_code=200,
                json={
                    "choices": [{
                        "message": {
                            "content": json.dumps(
                                {
                                    "papers": [
                                        {"id": paper_id, "relevance": 9.0, "reason": "kimi"}
                                        for paper_id in paper_ids
                                    ]
                                }
                            )
                        }
                    }],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 50},
                },
            )

        chain = LLMChain(
            db_session,
            app_config=config,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        try:
            result = await run_llm_rank(shortlist, db_session, llm_chain=chain)
        finally:
            await chain.aclose()

        assert result["degraded"] is False
        assert chain.breaker.snapshot("deepseek").consecutive_failures == 2
        for paper in shortlist:
            await db_session.refresh(paper)
            assert paper.llm_score == 9.0
            assert paper.llm_reason == "kimi"

    @pytest.mark.asyncio
    async def test_returns_degraded_when_all_providers_fail(self, db_session, monkeypatch):
        _set_provider_env(monkeypatch)
        config = copy.deepcopy(merge_app_config())
        config["llm"]["chain"] = ["deepseek", "kimi"]
        await _set_app_config(db_session, config)

        shortlist = await _make_papers(db_session, venue_count=2, arxiv_count=2)

        def handler(request):
            return httpx.Response(status_code=500, json={"error": "boom"})

        chain = LLMChain(
            db_session,
            app_config=config,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        try:
            result = await run_llm_rank(shortlist, db_session, llm_chain=chain)
        finally:
            await chain.aclose()

        assert result["degraded"] is True
        for paper in shortlist:
            await db_session.refresh(paper)
            assert paper.final_score == paper.prefilter_score
