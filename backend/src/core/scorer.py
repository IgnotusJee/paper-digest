"""Scoring functions for paper evaluation. Pure computations, no DB access."""
import math
from datetime import datetime, UTC

from ..config import APP_CONFIG


def keyword_match(paper_title: str, paper_abstract: str | None, keywords: list) -> float:
    """Match paper title+abstract against keyword entries (main + aliases).
    
    Returns normalized score in [0, 1].
    Each keyword has weight > 0 (interested) or < 0 (exclude).
    """
    if not keywords:
        return 0.0

    text = (paper_title or "").lower()
    if paper_abstract:
        text += " " + paper_abstract.lower()

    total_weight = 0.0
    matched_weight = 0.0

    for kw in keywords:
        weight = kw.weight if hasattr(kw, "weight") else kw.get("weight", 1.0)
        total_weight += abs(weight)

        term = (kw.keyword if hasattr(kw, "keyword") else kw.get("keyword", "")).lower()
        aliases = kw.aliases if hasattr(kw, "aliases") else (kw.get("aliases") or [])
        aliases_lower = [a.lower() for a in (aliases or [])]

        matched = False
        if term and term in text:
            matched = True
        elif aliases_lower:
            for alias in aliases_lower:
                if alias in text:
                    matched = True
                    break

        if matched:
            matched_weight += weight

    if total_weight == 0:
        return 0.0

    return max(0.0, min(1.0, matched_weight / total_weight))


def recency_score(paper_created_at: datetime | None) -> float:
    """Exponential decay with 7-day half-life.
    
    score = 0.5 ^ (days / 7)
    """
    if paper_created_at is None:
        return 0.0

    now = datetime.now(UTC).replace(tzinfo=None)
    if paper_created_at.tzinfo is not None:
        paper_created_at = paper_created_at.replace(tzinfo=None)

    delta = now - paper_created_at
    days = max(delta.total_seconds() / 86400.0, 0.0)
    return 0.5 ** (days / 7.0)


def source_prior(venue: str | None, venue_hint: str | None, app_config: dict | None = None) -> float:
    """Source priority based on publication status.
    
    venue in config venues list -> 1.0
    venue_hint present -> 0.8
    pure arxiv preprint -> 0.6
    """
    app_config = app_config or APP_CONFIG

    if venue:
        buckets_cfg = app_config.get("sources", {}).get("buckets", [])
        venue_bucket = next((b for b in buckets_cfg if b.get("name") == "venue"), None)
        if venue_bucket and venue in venue_bucket.get("venues", []):
            return 1.0
        return 0.8

    if venue_hint:
        return 0.8

    return 0.6


def prefilter_score(
    keyword_score: float,
    personal_score: float,
    recency: float,
    source: float,
    has_personal: bool,
    app_config: dict | None = None,
) -> float:
    """Weighted combination of all pre-LLM signals.
    
    When has_personal=False, personal weight is folded into keyword.
    """
    app_config = app_config or APP_CONFIG
    weights = app_config.get("scoring", {}).get("prefilter", {})
    w_kw = weights.get("keyword", 0.45)
    w_per = weights.get("personal", 0.30)
    w_rec = weights.get("recency", 0.15)
    w_src = weights.get("source_prior", 0.10)

    if not has_personal:
        w_kw = w_kw + w_per
        w_per = 0.0

    return w_kw * keyword_score + w_per * personal_score + w_rec * recency + w_src * source
