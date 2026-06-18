from datetime import UTC, datetime, timedelta

import httpx
import pytest

from src.config import merge_app_config
from src.core.llm_client import BATCH_SCORE_SCHEMA, LLMChain, LLMUnavailable, _parse_or_retry
from src.models import SystemConfig


def _app_config(**llm_overrides):
    config = merge_app_config()
    config["llm"].update(llm_overrides)
    return config


def _json_response(
    content: str,
    usage: dict | None = None,
    status_code: int = 200,
    include_usage: bool = True,
) -> httpx.Response:
    body = {
        "choices": [{"message": {"content": content}}],
    }
    if include_usage:
        body["usage"] = usage or {"prompt_tokens": 120, "completion_tokens": 80}
    return httpx.Response(status_code=status_code, json=body)


def _set_provider_env(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://deepseek.test/v1")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-chat")
    monkeypatch.setenv("KIMI_API_KEY", "kimi-key")
    monkeypatch.setenv("KIMI_BASE_URL", "https://kimi.test/v1")
    monkeypatch.setenv("KIMI_MODEL", "moonshot-v1-8k")


async def _make_chain(db_session, monkeypatch, handler, app_config=None, now_fn=None):
    _set_provider_env(monkeypatch)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    chain = LLMChain(
        db_session,
        app_config=app_config or _app_config(chain=["deepseek"]),
        http_client=client,
        now_fn=now_fn,
    )
    return chain


async def _get_cost_value(db_session, day: datetime) -> float | None:
    row = await db_session.get(SystemConfig, f"cost:{day.date().isoformat()}")
    return None if row is None else float(row.value)


class TestParseOrRetry:
    def test_repairs_noisy_json(self):
        data = _parse_or_retry(
            'Here is the result\n{"papers":[{"id":1,"relevance":8,"reason":"fit"}]}\nThanks',
            BATCH_SCORE_SCHEMA,
        )
        assert data["papers"][0]["id"] == 1

    def test_repairs_truncated_json(self):
        data = _parse_or_retry(
            '{"papers":[{"id":1,"relevance":8,"reason":"fit"}]',
            BATCH_SCORE_SCHEMA,
        )
        assert data["papers"][0]["relevance"] == 8


class TestLLMChain:
    @pytest.mark.asyncio
    async def test_chat_json_success(self, db_session, monkeypatch):
        now = datetime(2026, 6, 17, tzinfo=UTC)

        def handler(request):
            assert request.url.host == "deepseek.test"
            return _json_response('{"papers":[{"id":1,"relevance":8.5,"reason":"strong fit"}]}')

        chain = await _make_chain(
            db_session,
            monkeypatch,
            handler,
            app_config=_app_config(chain=["deepseek"]),
            now_fn=lambda: now,
        )
        try:
            result = await chain.chat_json([{"role": "user", "content": "score this"}], BATCH_SCORE_SCHEMA)
        finally:
            await chain.aclose()

        assert result["papers"][0]["id"] == 1
        cost_row = await db_session.get(SystemConfig, "cost:2026-06-17")
        assert cost_row is not None
        assert float(cost_row.value) > 0

    @pytest.mark.asyncio
    async def test_invalid_schema_counts_as_provider_failure(self, db_session, monkeypatch):
        now = datetime(2026, 6, 17, tzinfo=UTC)

        def handler(request):
            return _json_response('{"papers":[{"id":1,"relevance":11,"reason":"too high"}]}')

        chain = await _make_chain(
            db_session,
            monkeypatch,
            handler,
            app_config=_app_config(chain=["deepseek"]),
            now_fn=lambda: now,
        )
        try:
            with pytest.raises(LLMUnavailable):
                await chain.chat_json([{"role": "user", "content": "score this"}], BATCH_SCORE_SCHEMA)
        finally:
            await chain.aclose()

        state = chain.breaker.snapshot("deepseek")
        assert state.consecutive_failures == 1
        assert await _get_cost_value(db_session, now) is not None

    @pytest.mark.asyncio
    async def test_validator_failure_still_records_usage(self, db_session, monkeypatch):
        now = datetime(2026, 6, 17, tzinfo=UTC)

        def handler(request):
            return _json_response('{"papers":[{"id":1,"relevance":8,"reason":"fit"}]}')

        chain = await _make_chain(
            db_session,
            monkeypatch,
            handler,
            app_config=_app_config(chain=["deepseek"]),
            now_fn=lambda: now,
        )
        try:
            with pytest.raises(LLMUnavailable):
                await chain.chat_json(
                    [{"role": "user", "content": "score this"}],
                    BATCH_SCORE_SCHEMA,
                    validator=lambda _: (_ for _ in ()).throw(ValueError("validator failed")),
                )
        finally:
            await chain.aclose()

        state = chain.breaker.snapshot("deepseek")
        assert state.consecutive_failures == 1
        assert await _get_cost_value(db_session, now) is not None

    @pytest.mark.asyncio
    async def test_daily_budget_blocks_call(self, db_session, monkeypatch):
        calls = 0

        def handler(request):
            nonlocal calls
            calls += 1
            return _json_response('{"papers":[{"id":1,"relevance":8,"reason":"fit"}]}')

        chain = await _make_chain(
            db_session,
            monkeypatch,
            handler,
            app_config=_app_config(chain=["deepseek"], daily_budget=0.000001),
            now_fn=lambda: datetime(2026, 6, 17, tzinfo=UTC),
        )
        try:
            with pytest.raises(LLMUnavailable):
                await chain.chat_json([{"role": "user", "content": "score this"}], BATCH_SCORE_SCHEMA)
        finally:
            await chain.aclose()

        assert calls == 0

    @pytest.mark.asyncio
    async def test_max_cost_per_call_blocks_call(self, db_session, monkeypatch):
        calls = 0

        def handler(request):
            nonlocal calls
            calls += 1
            return _json_response('{"papers":[{"id":1,"relevance":8,"reason":"fit"}]}')

        chain = await _make_chain(
            db_session,
            monkeypatch,
            handler,
            app_config=_app_config(chain=["deepseek"], max_cost_per_call=0.000001),
        )
        try:
            with pytest.raises(LLMUnavailable):
                await chain.chat_json([{"role": "user", "content": "score this"}], BATCH_SCORE_SCHEMA)
        finally:
            await chain.aclose()

        assert calls == 0

    @pytest.mark.asyncio
    async def test_circuit_opens_after_three_failures_and_skips_fourth(self, db_session, monkeypatch):
        calls = 0

        def handler(request):
            nonlocal calls
            calls += 1
            return httpx.Response(status_code=500, json={"error": "boom"})

        chain = await _make_chain(
            db_session,
            monkeypatch,
            handler,
            app_config=_app_config(chain=["deepseek"], circuit_threshold=3, circuit_cooldown_sec=600),
            now_fn=lambda: datetime(2026, 6, 17, tzinfo=UTC),
        )
        try:
            for _ in range(4):
                with pytest.raises(LLMUnavailable):
                    await chain.chat_json([{"role": "user", "content": "score this"}], BATCH_SCORE_SCHEMA)
        finally:
            await chain.aclose()

        state = chain.breaker.snapshot("deepseek")
        assert calls == 3
        assert state.state == "open"

    @pytest.mark.asyncio
    async def test_http_failure_does_not_record_spend(self, db_session, monkeypatch):
        now = datetime(2026, 6, 17, tzinfo=UTC)

        def handler(request):
            return httpx.Response(status_code=500, json={"error": "boom"})

        chain = await _make_chain(
            db_session,
            monkeypatch,
            handler,
            app_config=_app_config(chain=["deepseek"]),
            now_fn=lambda: now,
        )
        try:
            with pytest.raises(LLMUnavailable):
                await chain.chat_json([{"role": "user", "content": "score this"}], BATCH_SCORE_SCHEMA)
        finally:
            await chain.aclose()

        assert await _get_cost_value(db_session, now) is None

    @pytest.mark.asyncio
    async def test_missing_usage_does_not_record_spend(self, db_session, monkeypatch):
        now = datetime(2026, 6, 17, tzinfo=UTC)

        def handler(request):
            return _json_response(
                '{"papers":[{"id":1,"relevance":8,"reason":"fit"}]}',
                include_usage=False,
            )

        chain = await _make_chain(
            db_session,
            monkeypatch,
            handler,
            app_config=_app_config(chain=["deepseek"]),
            now_fn=lambda: now,
        )
        try:
            result = await chain.chat_json([{"role": "user", "content": "score this"}], BATCH_SCORE_SCHEMA)
        finally:
            await chain.aclose()

        assert result["papers"][0]["id"] == 1
        assert await _get_cost_value(db_session, now) is None

    @pytest.mark.asyncio
    async def test_half_open_recovers_after_cooldown(self, db_session, monkeypatch):
        calls = 0
        now_holder = {"value": datetime(2026, 6, 17, tzinfo=UTC)}

        def handler(request):
            nonlocal calls
            calls += 1
            if calls == 1:
                return httpx.Response(status_code=500, json={"error": "boom"})
            return _json_response('{"papers":[{"id":1,"relevance":9,"reason":"recovered"}]}')

        chain = await _make_chain(
            db_session,
            monkeypatch,
            handler,
            app_config=_app_config(chain=["deepseek"], circuit_threshold=1, circuit_cooldown_sec=60),
            now_fn=lambda: now_holder["value"],
        )
        try:
            with pytest.raises(LLMUnavailable):
                await chain.chat_json([{"role": "user", "content": "score this"}], BATCH_SCORE_SCHEMA)

            now_holder["value"] = now_holder["value"] + timedelta(seconds=61)
            result = await chain.chat_json([{"role": "user", "content": "score this"}], BATCH_SCORE_SCHEMA)
        finally:
            await chain.aclose()

        state = chain.breaker.snapshot("deepseek")
        assert calls == 2
        assert result["papers"][0]["reason"] == "recovered"
        assert state.state == "closed"
