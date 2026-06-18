import copy
import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession

load_dotenv()

DATABASE_URL: str = os.environ["DATABASE_URL"]
JWT_SECRET: str = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 12

BASE_URL: str = os.environ.get("BASE_URL", "http://localhost:8000")

_cfg_path = Path(__file__).parent.parent / "config" / "default.json"
with open(_cfg_path) as _f:
    APP_CONFIG: dict = json.load(_f)

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_APP_CONFIG_KEY = "app_config"
_APP_CONFIG_SECTIONS = ("sources", "scoring", "recommender", "llm", "scheduler")
logger = logging.getLogger(__name__)


def _deep_merge(base: Any, override: Any) -> Any:
    if not isinstance(base, dict) or not isinstance(override, dict):
        return copy.deepcopy(override)

    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def get_default_app_config() -> dict:
    return copy.deepcopy(APP_CONFIG)


def merge_app_config(override: dict | None = None) -> dict:
    merged = get_default_app_config()
    if override:
        merged = _deep_merge(merged, override)
    return {section: copy.deepcopy(merged.get(section, {})) for section in _APP_CONFIG_SECTIONS}


def normalize_app_config(config: dict) -> dict:
    if not isinstance(config, dict):
        raise ValueError("settings payload must be an object")

    normalized: dict[str, dict] = {}
    for section in _APP_CONFIG_SECTIONS:
        value = config.get(section)
        if not isinstance(value, dict):
            raise ValueError(f"{section} must be an object")
        normalized[section] = copy.deepcopy(value)
    return normalized


def _is_positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_non_negative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _validate_string_array(value: Any, path: str) -> None:
    if not isinstance(value, list):
        raise ValueError(f"{path} must be an array")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{path} items must be non-empty strings")


def validate_app_config(config: dict) -> dict:
    normalized = normalize_app_config(config)

    sources = normalized["sources"]
    fill_policy = sources.get("fill_policy")
    if fill_policy not in {"strict", "spillover"}:
        raise ValueError("sources.fill_policy must be one of: strict, spillover")

    if not _is_non_negative_int(sources.get("daily_total")):
        raise ValueError("sources.daily_total must be an integer >= 0")
    if not isinstance(sources.get("oversample"), int) or isinstance(sources.get("oversample"), bool) or sources["oversample"] < 1:
        raise ValueError("sources.oversample must be an integer >= 1")

    buckets = sources.get("buckets")
    if not isinstance(buckets, list):
        raise ValueError("sources.buckets must be an array")
    if len(buckets) != 2:
        raise ValueError("sources.buckets must contain exactly 2 buckets")

    for bucket in buckets:
        if not isinstance(bucket, dict):
            raise ValueError("sources.buckets items must be objects")
        name = bucket.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("bucket.name must be a non-empty string")

    bucket_names = [bucket["name"] for bucket in buckets]
    if bucket_names != ["venue", "arxiv"]:
        raise ValueError("sources.buckets must be ordered as [venue, arxiv]")

    venue_bucket = buckets[0]
    arxiv_bucket = buckets[1]

    if not _is_non_negative_int(venue_bucket.get("quota")):
        raise ValueError("sources.buckets[0].quota must be an integer >= 0")
    if not _is_non_negative_int(arxiv_bucket.get("quota")):
        raise ValueError("sources.buckets[1].quota must be an integer >= 0")

    if "enabled" in venue_bucket and not isinstance(venue_bucket["enabled"], bool):
        raise ValueError("sources.buckets[0].enabled must be a boolean")
    if "enabled" in arxiv_bucket and not isinstance(arxiv_bucket["enabled"], bool):
        raise ValueError("sources.buckets[1].enabled must be a boolean")

    _validate_string_array(venue_bucket.get("venues"), "sources.buckets[0].venues")
    if "include_venue_hint" in venue_bucket and not isinstance(venue_bucket["include_venue_hint"], bool):
        raise ValueError("sources.buckets[0].include_venue_hint must be a boolean")
    if "include_dblp" in venue_bucket and not isinstance(venue_bucket["include_dblp"], bool):
        raise ValueError("sources.buckets[0].include_dblp must be a boolean")

    _validate_string_array(arxiv_bucket.get("arxiv_categories"), "sources.buckets[1].arxiv_categories")

    scoring = normalized["scoring"]
    prefilter = scoring.get("prefilter")
    if not isinstance(prefilter, dict):
        raise ValueError("scoring.prefilter must be an object")

    weight_fields = ("keyword", "personal", "recency", "source_prior")
    total_weight = 0.0
    for field in weight_fields:
        value = prefilter.get(field)
        if not _is_number(value):
            raise ValueError(f"scoring.prefilter.{field} must be a number")
        total_weight += float(value)
    if abs(total_weight - 1.0) > 1e-6:
        raise ValueError("scoring.prefilter weights must sum to 1.0")

    recommender = normalized["recommender"]
    for field in ("min_pos_centroid", "min_pos_model", "min_neg_model"):
        value = recommender.get(field)
        if not _is_non_negative_int(value):
            raise ValueError(f"recommender.{field} must be an integer >= 0")

    llm = normalized["llm"]
    if not _is_positive_number(llm.get("daily_budget")):
        raise ValueError("llm.daily_budget must be > 0")
    if not _is_positive_number(llm.get("max_cost_per_call")):
        raise ValueError("llm.max_cost_per_call must be > 0")
    if not isinstance(llm.get("batch_size"), int) or llm["batch_size"] < 1:
        raise ValueError("llm.batch_size must be >= 1")
    if not isinstance(llm.get("circuit_threshold"), int) or isinstance(llm.get("circuit_threshold"), bool) or llm["circuit_threshold"] < 1:
        raise ValueError("llm.circuit_threshold must be an integer >= 1")
    if not _is_non_negative_int(llm.get("circuit_cooldown_sec")):
        raise ValueError("llm.circuit_cooldown_sec must be an integer >= 0")

    chain = llm.get("chain")
    if not isinstance(chain, list) or not chain:
        raise ValueError("llm.chain must be a non-empty array")
    if any(not isinstance(item, str) or not item.strip() for item in chain):
        raise ValueError("llm.chain items must be non-empty strings")

    return normalized


async def get_system_config_value(db: AsyncSession, key: str) -> str | None:
    from .models import SystemConfig

    row = await db.get(SystemConfig, key)
    return row.value if row else None


async def set_system_config_value(db: AsyncSession, key: str, value: str) -> None:
    from .models import SystemConfig

    row = await db.get(SystemConfig, key)
    if row:
        row.value = value
    else:
        db.add(SystemConfig(key=key, value=value))


async def get_app_config_override(db: AsyncSession) -> dict | None:
    raw_value = await get_system_config_value(db, _APP_CONFIG_KEY)
    if raw_value is None:
        return None

    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError:
        logger.warning("Invalid app_config JSON in system_config, ignoring override")
        return None

    if not isinstance(value, dict):
        logger.warning("app_config override is not an object, ignoring override")
        return None
    return value


async def get_app_config(db: AsyncSession) -> dict:
    return merge_app_config(await get_app_config_override(db))


async def save_app_config(db: AsyncSession, config: dict) -> dict:
    normalized = validate_app_config(config)
    await set_system_config_value(
        db,
        _APP_CONFIG_KEY,
        json.dumps(normalized, ensure_ascii=False, sort_keys=True),
    )
    await db.commit()
    return merge_app_config(normalized)


def load_prompt(name: str) -> str:
    path = _PROMPTS_DIR / f"{name}.txt"
    return path.read_text(encoding="utf-8")
