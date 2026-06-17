import pytest
from src.core.dedup import norm_title, title_hash, find_duplicate, merge_into
from src.models import Paper


class TestNormTitle:
    def test_lowercase(self):
        assert norm_title("Hello World") == "hello world"

    def test_strip_punctuation(self):
        assert norm_title("Hello, World! (2025)") == "hello world 2025"

    def test_collapse_whitespace(self):
        assert norm_title("  hello   world  ") == "hello world"

    def test_combined(self):
        assert norm_title("  A Title: With (Punctuation)  ") == "a title with punctuation"


class TestTitleHash:
    def test_deterministic(self):
        assert title_hash("Hello World") == title_hash("Hello World")

    def test_length(self):
        assert len(title_hash("anything")) == 16

    def test_different_titles(self):
        assert title_hash("Title A") != title_hash("Title B")

    def test_normalized_equality(self):
        assert title_hash("Hello World") == title_hash("hello, world!")


class TestFindDuplicate:
    @pytest.mark.asyncio
    async def test_by_doi(self, db_session, sample_raw):
        paper = Paper(
            title="Test", title_hash="abc123", source="dblp",
            doi="10.1234/test", arxiv_id=None,
        )
        db_session.add(paper)
        await db_session.commit()

        raw = sample_raw(doi="10.1234/test")
        result = await find_duplicate(raw, db_session)
        assert result is not None
        assert result.id == paper.id

    @pytest.mark.asyncio
    async def test_by_arxiv_id(self, db_session, sample_raw):
        paper = Paper(
            title="Test", title_hash="abc123", source="arxiv",
            arxiv_id="2506.12345v1",
        )
        db_session.add(paper)
        await db_session.commit()

        raw = sample_raw(doi=None)
        result = await find_duplicate(raw, db_session)
        assert result is not None
        assert result.id == paper.id

    @pytest.mark.asyncio
    async def test_by_title_hash(self, db_session, sample_raw):
        paper = Paper(
            title="Test Paper: A Study of Distributed Systems",
            title_hash=title_hash("Test Paper: A Study of Distributed Systems"),
            source="arxiv",
        )
        db_session.add(paper)
        await db_session.commit()

        raw = sample_raw(doi=None, arxiv_id="9999.99999v1")
        result = await find_duplicate(raw, db_session)
        assert result is not None
        assert result.id == paper.id

    @pytest.mark.asyncio
    async def test_no_match(self, db_session, sample_raw):
        raw = sample_raw()
        result = await find_duplicate(raw, db_session)
        assert result is None


class TestMergeInto:
    def test_fills_venue_hint(self, sample_raw):
        existing = Paper(
            title="Test", title_hash="abc", source="arxiv",
            venue_hint=None,
        )
        raw = sample_raw()
        merge_into(existing, raw, "OSDI", "venue")
        assert existing.venue_hint == "OSDI"

    def test_preserves_existing_venue_hint(self, sample_raw):
        existing = Paper(
            title="Test", title_hash="abc", source="arxiv",
            venue_hint="SOSP",
        )
        raw = sample_raw()
        merge_into(existing, raw, "OSDI", "venue")
        assert existing.venue_hint == "SOSP"

    def test_preserves_pushed_state(self, sample_raw):
        existing = Paper(
            title="Test", title_hash="abc", source="arxiv",
            pushed=True,
        )
        raw = sample_raw()
        merge_into(existing, raw, None, "arxiv")
        assert existing.pushed is True

    def test_preserves_venue_bucket_for_existing_venue_record(self, sample_raw):
        existing = Paper(
            title="Test", title_hash="abc", source="dblp",
            venue="OSDI",
            bucket=None,
        )
        raw = sample_raw(comments=None)
        merge_into(existing, raw, None, "arxiv")
        assert existing.bucket == "venue"

    def test_upgrades_existing_arxiv_bucket_when_venue_hint_appears(self, sample_raw):
        existing = Paper(
            title="Test", title_hash="abc", source="arxiv",
            bucket="arxiv",
        )
        raw = sample_raw()
        merge_into(existing, raw, "SOSP", "venue")
        assert existing.bucket == "venue"

    def test_updates_abstract(self, sample_raw):
        existing = Paper(
            title="Test", title_hash="abc", source="arxiv",
            abstract_en="old abstract",
        )
        raw = sample_raw(abstract="new abstract")
        merge_into(existing, raw, None, "arxiv")
        assert existing.abstract_en == "new abstract"

    def test_fills_missing_doi(self, sample_raw):
        existing = Paper(
            title="Test", title_hash="abc", source="arxiv",
            doi=None,
        )
        raw = sample_raw(doi="10.1234/test")
        merge_into(existing, raw, None, "arxiv")
        assert existing.doi == "10.1234/test"

    def test_does_not_overwrite_doi(self, sample_raw):
        existing = Paper(
            title="Test", title_hash="abc", source="arxiv",
            doi="10.1234/existing",
        )
        raw = sample_raw(doi="10.1234/new")
        merge_into(existing, raw, None, "arxiv")
        assert existing.doi == "10.1234/existing"
