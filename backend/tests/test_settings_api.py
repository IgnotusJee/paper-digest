import copy

import pytest

from src.config import merge_app_config


def _base_config():
    return copy.deepcopy(merge_app_config())


def _rename_bucket(config):
    config["sources"]["buckets"][0]["name"] = "conference"


def _reverse_bucket_order(config):
    config["sources"]["buckets"].reverse()


def _remove_venue_bucket(config):
    config["sources"]["buckets"] = [config["sources"]["buckets"][1]]


def _remove_arxiv_bucket(config):
    config["sources"]["buckets"] = [config["sources"]["buckets"][0]]


def _set_venue_list_to_string(config):
    config["sources"]["buckets"][0]["venues"] = "FAST"


def _set_venue_list_with_empty_entry(config):
    config["sources"]["buckets"][0]["venues"] = ["FAST", ""]


def _set_arxiv_categories_to_string(config):
    config["sources"]["buckets"][1]["arxiv_categories"] = "cs.DC"


def _set_arxiv_categories_with_empty_entry(config):
    config["sources"]["buckets"][1]["arxiv_categories"] = ["cs.DC", ""]


def _set_string_prefilter_weight(config):
    config["scoring"]["prefilter"]["keyword"] = "0.45"


def _set_string_recommender_threshold(config):
    config["recommender"]["min_pos_centroid"] = "1"


def _set_invalid_oversample(config):
    config["sources"]["oversample"] = 0


def _set_invalid_daily_total(config):
    config["sources"]["daily_total"] = -1


def _set_invalid_circuit_threshold(config):
    config["llm"]["circuit_threshold"] = 0


def _set_invalid_circuit_cooldown(config):
    config["llm"]["circuit_cooldown_sec"] = -1


def _set_invalid_prefilter_sum(config):
    config["scoring"]["prefilter"]["keyword"] = 0.5


class TestSettingsAuth:
    @pytest.mark.asyncio
    async def test_unauthorized(self, client):
        resp = await client.get("/api/settings")
        assert resp.status_code == 401


class TestSettingsApi:
    @pytest.mark.asyncio
    async def test_get_returns_default_config(self, auth_client):
        resp = await auth_client.get("/api/settings")
        assert resp.status_code == 200
        assert resp.json() == merge_app_config()

    @pytest.mark.asyncio
    async def test_put_overrides_and_get_returns_merged_config(self, auth_client):
        config = _base_config()
        config["sources"]["fill_policy"] = "spillover"
        config["sources"]["buckets"][0]["quota"] = 2
        config["llm"]["daily_budget"] = 0.75
        config["llm"]["batch_size"] = 8

        put_resp = await auth_client.put("/api/settings", json=config)
        assert put_resp.status_code == 200
        assert put_resp.json() == config

        get_resp = await auth_client.get("/api/settings")
        assert get_resp.status_code == 200
        assert get_resp.json() == config

    @pytest.mark.asyncio
    async def test_rejects_invalid_fill_policy(self, auth_client):
        config = _base_config()
        config["sources"]["fill_policy"] = "invalid"

        resp = await auth_client.put("/api/settings", json=config)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_rejects_invalid_bucket_quota(self, auth_client):
        config = _base_config()
        config["sources"]["buckets"][0]["quota"] = -1

        resp = await auth_client.put("/api/settings", json=config)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_rejects_invalid_llm_params(self, auth_client):
        config = _base_config()
        config["llm"]["daily_budget"] = 0

        resp = await auth_client.put("/api/settings", json=config)
        assert resp.status_code == 400

        config = _base_config()
        config["llm"]["max_cost_per_call"] = 0
        resp = await auth_client.put("/api/settings", json=config)
        assert resp.status_code == 400

        config = _base_config()
        config["llm"]["batch_size"] = 0
        resp = await auth_client.put("/api/settings", json=config)
        assert resp.status_code == 400

        config = _base_config()
        config["llm"]["chain"] = []
        resp = await auth_client.put("/api/settings", json=config)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("mutator", "detail"),
        [
            (_rename_bucket, "sources.buckets"),
            (_reverse_bucket_order, "sources.buckets"),
            (_remove_venue_bucket, "sources.buckets"),
            (_remove_arxiv_bucket, "sources.buckets"),
            (_set_venue_list_to_string, "sources.buckets[0].venues"),
            (_set_venue_list_with_empty_entry, "sources.buckets[0].venues"),
            (_set_arxiv_categories_to_string, "sources.buckets[1].arxiv_categories"),
            (_set_arxiv_categories_with_empty_entry, "sources.buckets[1].arxiv_categories"),
            (_set_string_prefilter_weight, "scoring.prefilter.keyword"),
            (_set_string_recommender_threshold, "recommender.min_pos_centroid"),
            (_set_invalid_oversample, "sources.oversample"),
            (_set_invalid_daily_total, "sources.daily_total"),
            (_set_invalid_circuit_threshold, "llm.circuit_threshold"),
            (_set_invalid_circuit_cooldown, "llm.circuit_cooldown_sec"),
            (_set_invalid_prefilter_sum, "scoring.prefilter weights must sum to 1.0"),
        ],
    )
    async def test_rejects_unsupported_bucket_and_numeric_settings(self, auth_client, mutator, detail):
        config = _base_config()
        mutator(config)

        resp = await auth_client.put("/api/settings", json=config)
        assert resp.status_code == 400
        assert detail in resp.json()["detail"]
