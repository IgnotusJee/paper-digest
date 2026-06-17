import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")

from datetime import datetime, timedelta, UTC
import pytest
from unittest.mock import MagicMock

from src.core.scorer import keyword_match, recency_score, source_prior, prefilter_score


class TestKeywordMatch:
    def test_basic_match(self):
        kw = MagicMock(keyword="distributed systems", weight=1.0, aliases=[])
        score = keyword_match("A Study of Distributed Systems", None, [kw])
        assert 0.0 < score <= 1.0

    def test_no_match(self):
        kw = MagicMock(keyword="quantum computing", weight=1.0, aliases=[])
        score = keyword_match("A Study of Distributed Systems", None, [kw])
        assert score == 0.0

    def test_alias_match(self):
        kw = MagicMock(keyword="large language model", weight=1.0, aliases=["LLM"])
        score = keyword_match("Efficient LLM Inference", None, [kw])
        assert score > 0.0

    def test_abstract_match(self):
        kw = MagicMock(keyword="transformer", weight=1.0, aliases=[])
        score = keyword_match("Title", "We propose a new transformer architecture", [kw])
        assert score > 0.0

    def test_weighted_keywords(self):
        kw_pos = MagicMock(keyword="LLM", weight=1.0, aliases=[])
        kw_neg = MagicMock(keyword="quantum", weight=-0.5, aliases=[])
        score = keyword_match("LLM Inference Study", None, [kw_pos, kw_neg])
        assert 0.0 < score < 1.0

    def test_empty_keywords(self):
        score = keyword_match("Any Paper", None, [])
        assert score == 0.0

    def test_normalized_range(self):
        kw = MagicMock(keyword="test", weight=1.0, aliases=[])
        score = keyword_match("test paper with test keyword", "test abstract", [kw])
        assert 0.0 <= score <= 1.0

    def test_multiple_keywords(self):
        kw1 = MagicMock(keyword="LLM", weight=1.0, aliases=[])
        kw2 = MagicMock(keyword="inference", weight=1.0, aliases=[])
        score = keyword_match("LLM Inference Optimization", None, [kw1, kw2])
        assert score == 1.0


class TestRecencyScore:
    def test_today(self):
        now = datetime.now(UTC).replace(tzinfo=None)
        score = recency_score(now)
        assert score >= 0.99

    def test_seven_days_half_life(self):
        seven_days_ago = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=7)
        score = recency_score(seven_days_ago)
        assert abs(score - 0.5) < 0.05

    def test_fourteen_days(self):
        fourteen_days_ago = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=14)
        score = recency_score(fourteen_days_ago)
        assert abs(score - 0.25) < 0.05

    def test_none_returns_zero(self):
        assert recency_score(None) == 0.0

    def test_old_paper(self):
        old = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=100)
        score = recency_score(old)
        assert score < 0.01


class TestSourcePrior:
    def test_venue_match(self, monkeypatch):
        monkeypatch.setattr("src.core.scorer.APP_CONFIG", {
            "sources": {"buckets": [{"name": "venue", "venues": ["FAST", "OSDI"]}]}
        })
        assert source_prior("FAST", None) == 1.0

    def test_venue_not_in_list(self, monkeypatch):
        monkeypatch.setattr("src.core.scorer.APP_CONFIG", {
            "sources": {"buckets": [{"name": "venue", "venues": ["FAST"]}]}
        })
        assert source_prior("RANDOM_CONF", None) == 0.8

    def test_venue_hint(self):
        assert source_prior(None, "OSDI") == 0.8

    def test_pure_arxiv(self):
        assert source_prior(None, None) == 0.6


class TestPrefilterScore:
    def test_combination(self, monkeypatch):
        monkeypatch.setattr("src.core.scorer.APP_CONFIG", {
            "scoring": {"prefilter": {"keyword": 0.45, "personal": 0.30, "recency": 0.15, "source_prior": 0.10}}
        })
        result = prefilter_score(0.8, 0.6, 0.5, 1.0, True)
        expected = 0.45 * 0.8 + 0.30 * 0.6 + 0.15 * 0.5 + 0.10 * 1.0
        assert abs(result - expected) < 1e-6

    def test_personal_folded(self, monkeypatch):
        monkeypatch.setattr("src.core.scorer.APP_CONFIG", {
            "scoring": {"prefilter": {"keyword": 0.45, "personal": 0.30, "recency": 0.15, "source_prior": 0.10}}
        })
        result = prefilter_score(0.8, 0.5, 0.5, 1.0, False)
        expected = 0.75 * 0.8 + 0.0 * 0.5 + 0.15 * 0.5 + 0.10 * 1.0
        assert abs(result - expected) < 1e-6

    def test_all_zeros(self, monkeypatch):
        monkeypatch.setattr("src.core.scorer.APP_CONFIG", {
            "scoring": {"prefilter": {"keyword": 0.45, "personal": 0.30, "recency": 0.15, "source_prior": 0.10}}
        })
        result = prefilter_score(0.0, 0.0, 0.0, 0.0, True)
        assert result == 0.0
