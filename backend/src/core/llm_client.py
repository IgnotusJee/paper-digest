import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Callable

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_app_config, get_system_config_value, set_system_config_value


class LLMUnavailable(RuntimeError):
    pass


@dataclass
class ProviderConfig:
    name: str
    api_key: str
    base_url: str
    model: str
    input_cost_per_1m: float
    output_cost_per_1m: float

    @property
    def endpoint(self) -> str:
        return f"{self.base_url.rstrip('/')}/chat/completions"

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return (
            (prompt_tokens / 1_000_000.0) * self.input_cost_per_1m
            + (completion_tokens / 1_000_000.0) * self.output_cost_per_1m
        )


@dataclass
class ProviderState:
    state: str = "closed"
    consecutive_failures: int = 0
    opened_at: datetime | None = None


class CircuitBreaker:
    def __init__(self) -> None:
        self._states: dict[str, ProviderState] = {}

    def _state(self, provider: str) -> ProviderState:
        return self._states.setdefault(provider, ProviderState())

    def allow(self, provider: str, threshold: int, cooldown_sec: int, now: datetime) -> bool:
        state = self._state(provider)
        if state.state != "open":
            return True

        if state.opened_at is None:
            state.opened_at = now
            return False

        if now - state.opened_at >= timedelta(seconds=cooldown_sec):
            state.state = "half_open"
            return True
        return False

    def record_success(self, provider: str) -> None:
        state = self._state(provider)
        state.state = "closed"
        state.consecutive_failures = 0
        state.opened_at = None

    def record_failure(self, provider: str, threshold: int, now: datetime) -> None:
        state = self._state(provider)
        state.consecutive_failures += 1
        if state.state == "half_open" or state.consecutive_failures >= threshold:
            state.state = "open"
            state.opened_at = now

    def snapshot(self, provider: str) -> ProviderState:
        state = self._state(provider)
        return ProviderState(
            state=state.state,
            consecutive_failures=state.consecutive_failures,
            opened_at=state.opened_at,
        )


DEFAULT_PROVIDER_CONFIGS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "input_cost_per_1m": 0.5,
        "output_cost_per_1m": 1.5,
    },
    "kimi": {
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k",
        "input_cost_per_1m": 0.6,
        "output_cost_per_1m": 1.6,
    },
}

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)

BATCH_SCORE_SCHEMA = {
    "type": "object",
    "required": ["papers"],
    "properties": {
        "papers": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "relevance", "reason"],
                "properties": {
                    "id": {"type": "integer"},
                    "relevance": {"type": "number", "minimum": 0, "maximum": 10},
                    "reason": {"type": "string"},
                },
            },
        }
    },
}

BATCH_TRANSLATE_SCHEMA = {
    "type": "object",
    "required": ["papers"],
    "properties": {
        "papers": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "title_cn", "abstract_cn", "summary_cn"],
                "properties": {
                    "id": {"type": "integer"},
                    "title_cn": {"type": "string"},
                    "abstract_cn": {"type": "string"},
                    "summary_cn": {
                        "type": "object",
                        "required": ["problem", "method", "value"],
                        "properties": {
                            "problem": {"type": "string"},
                            "method": {"type": "string"},
                            "value": {"type": "string"},
                        },
                    },
                },
            },
        }
    },
}


def _as_float(value: str | None, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _message_text_length(messages: list[dict[str, Any]]) -> int:
    total = 0
    for message in messages:
        content = message.get("content")
        if isinstance(content, str):
            total += len(content)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    total += len(item["text"])
    return total


def _extract_text_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts)
    raise ValueError("LLM response did not include text content")


def _strip_code_fence(raw: str) -> str:
    match = _JSON_BLOCK_RE.search(raw)
    if match:
        return match.group(1).strip()
    return raw.strip()


def _extract_json_candidate(raw: str) -> str:
    stripped = _strip_code_fence(raw)
    start_positions = [idx for idx in (stripped.find("{"), stripped.find("[")) if idx != -1]
    if not start_positions:
        return stripped

    start = min(start_positions)
    trimmed = stripped[start:]
    end_positions = [idx for idx in (trimmed.rfind("}"), trimmed.rfind("]")) if idx != -1]
    if end_positions:
        return trimmed[: max(end_positions) + 1].strip()
    return trimmed.strip()


def _repair_json_text(raw: str) -> str:
    candidate = _extract_json_candidate(raw)
    candidate = re.sub(r",(\s*[}\]])", r"\1", candidate)

    stack: list[str] = []
    in_string = False
    escaped = False
    chars = list(candidate)
    for ch in chars:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            stack.append("}")
        elif ch == "[":
            stack.append("]")
        elif ch in "}]":
            if stack and ch == stack[-1]:
                stack.pop()

    repaired = candidate
    if in_string:
        repaired += '"'
    repaired += "".join(reversed(stack))
    repaired = re.sub(r",(\s*[}\]])", r"\1", repaired)
    return repaired


def _validate_schema(data: Any, schema: dict[str, Any], path: str = "$") -> None:
    expected_type = schema.get("type")
    if expected_type == "object":
        if not isinstance(data, dict):
            raise ValueError(f"{path} must be an object")
        required = schema.get("required", [])
        for key in required:
            if key not in data:
                raise ValueError(f"{path}.{key} is required")
        properties = schema.get("properties", {})
        for key, value in data.items():
            if key in properties:
                _validate_schema(value, properties[key], f"{path}.{key}")
        return

    if expected_type == "array":
        if not isinstance(data, list):
            raise ValueError(f"{path} must be an array")
        if "minItems" in schema and len(data) < schema["minItems"]:
            raise ValueError(f"{path} must contain at least {schema['minItems']} items")
        if "maxItems" in schema and len(data) > schema["maxItems"]:
            raise ValueError(f"{path} must contain at most {schema['maxItems']} items")
        item_schema = schema.get("items")
        if item_schema:
            for idx, item in enumerate(data):
                _validate_schema(item, item_schema, f"{path}[{idx}]")
        return

    if expected_type == "string":
        if not isinstance(data, str):
            raise ValueError(f"{path} must be a string")
    elif expected_type == "integer":
        if not isinstance(data, int) or isinstance(data, bool):
            raise ValueError(f"{path} must be an integer")
    elif expected_type == "number":
        if not isinstance(data, (int, float)) or isinstance(data, bool):
            raise ValueError(f"{path} must be a number")

    if "enum" in schema and data not in schema["enum"]:
        raise ValueError(f"{path} must be one of {schema['enum']}")
    if "minimum" in schema and data < schema["minimum"]:
        raise ValueError(f"{path} must be >= {schema['minimum']}")
    if "maximum" in schema and data > schema["maximum"]:
        raise ValueError(f"{path} must be <= {schema['maximum']}")


def _parse_or_retry(raw: str, schema: dict[str, Any]) -> Any:
    try:
        data = json.loads(raw)
        _validate_schema(data, schema)
        return data
    except (json.JSONDecodeError, ValueError):
        repaired = _repair_json_text(raw)

    data = json.loads(repaired)
    _validate_schema(data, schema)
    return data


class LLMChain:
    def __init__(
        self,
        db: AsyncSession,
        app_config: dict | None = None,
        http_client: httpx.AsyncClient | None = None,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self.db = db
        self._app_config = app_config
        self._http_client = http_client
        self._now_fn = now_fn or (lambda: datetime.now(UTC))
        self.breaker = CircuitBreaker()

    async def _config(self) -> dict:
        if self._app_config is None:
            self._app_config = await get_app_config(self.db)
        return self._app_config

    def _provider_from_env(self, provider_name: str) -> ProviderConfig | None:
        defaults = DEFAULT_PROVIDER_CONFIGS.get(provider_name, {})
        prefix = provider_name.upper()
        api_key = os.environ.get(f"{prefix}_API_KEY", "").strip()
        if not api_key:
            return None

        base_url = os.environ.get(f"{prefix}_BASE_URL", defaults.get("base_url", "")).strip()
        model = os.environ.get(f"{prefix}_MODEL", defaults.get("model", "")).strip()
        if not base_url or not model:
            return None

        return ProviderConfig(
            name=provider_name,
            api_key=api_key,
            base_url=base_url,
            model=model,
            input_cost_per_1m=_as_float(
                os.environ.get(f"{prefix}_INPUT_COST_PER_1M"),
                defaults.get("input_cost_per_1m", 0.0),
            ),
            output_cost_per_1m=_as_float(
                os.environ.get(f"{prefix}_OUTPUT_COST_PER_1M"),
                defaults.get("output_cost_per_1m", 0.0),
            ),
        )

    async def _get_daily_cost(self, day: datetime) -> float:
        key = f"cost:{day.date().isoformat()}"
        raw = await get_system_config_value(self.db, key)
        if raw is None:
            return 0.0
        try:
            return float(raw)
        except ValueError:
            return 0.0

    async def _save_daily_cost(self, day: datetime, amount: float) -> None:
        key = f"cost:{day.date().isoformat()}"
        await set_system_config_value(self.db, key, f"{amount:.6f}")
        await self.db.commit()

    async def _budget_allows(self, provider: ProviderConfig, messages: list[dict[str, Any]], llm_cfg: dict) -> None:
        prompt_tokens = max(1, _message_text_length(messages) // 4)
        estimated_completion_tokens = max(256, prompt_tokens // 2)
        estimated_cost = provider.estimate_cost(prompt_tokens, estimated_completion_tokens)
        if estimated_cost > llm_cfg.get("max_cost_per_call", 0):
            raise LLMUnavailable(f"{provider.name} estimated cost exceeds max_cost_per_call")

        spent = await self._get_daily_cost(self._now_fn())
        if spent + estimated_cost > llm_cfg.get("daily_budget", 0):
            raise LLMUnavailable("daily budget exceeded")

    async def _record_usage(self, provider: ProviderConfig, usage: dict[str, Any] | None) -> None:
        usage = usage or {}
        prompt_tokens = usage.get("prompt_tokens", 0) or 0
        completion_tokens = usage.get("completion_tokens", 0) or 0
        actual_cost = provider.estimate_cost(prompt_tokens, completion_tokens)
        if actual_cost <= 0:
            return

        now = self._now_fn()
        spent = await self._get_daily_cost(now)
        await self._save_daily_cost(now, spent + actual_cost)

    async def _post_chat_completion(
        self,
        provider: ProviderConfig,
        messages: list[dict[str, Any]],
    ) -> tuple[str, dict[str, Any] | None]:
        payload = {
            "model": provider.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {provider.api_key}",
            "Content-Type": "application/json",
        }

        owns_client = self._http_client is None
        client = self._http_client or httpx.AsyncClient(timeout=30.0)
        try:
            response = await client.post(provider.endpoint, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        finally:
            if owns_client:
                await client.aclose()

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("LLM response missing choices[0].message.content") from exc

        return _extract_text_content(content), data.get("usage")

    async def chat_json(
        self,
        messages: list[dict[str, Any]],
        schema: dict[str, Any],
        validator: Callable[[Any], None] | None = None,
    ) -> Any:
        config = await self._config()
        llm_cfg = config.get("llm", {})
        threshold = llm_cfg.get("circuit_threshold", 3)
        cooldown_sec = llm_cfg.get("circuit_cooldown_sec", 600)
        now = self._now_fn()

        errors: list[str] = []
        for provider_name in llm_cfg.get("chain", []):
            provider = self._provider_from_env(provider_name)
            if provider is None:
                errors.append(f"{provider_name}: missing provider config")
                continue

            if not self.breaker.allow(provider.name, threshold, cooldown_sec, now):
                errors.append(f"{provider.name}: circuit open")
                continue

            try:
                await self._budget_allows(provider, messages, llm_cfg)
            except LLMUnavailable as exc:
                errors.append(f"{provider.name}: {exc}")
                continue

            try:
                raw_text, usage = await self._post_chat_completion(provider, messages)
                await self._record_usage(provider, usage)
                parsed = _parse_or_retry(raw_text, schema)
                if validator:
                    validator(parsed)
            except Exception as exc:
                self.breaker.record_failure(provider.name, threshold, now)
                errors.append(f"{provider.name}: {exc}")
                continue

            self.breaker.record_success(provider.name)
            return parsed

        raise LLMUnavailable("; ".join(errors) if errors else "No LLM providers available")

    async def aclose(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
