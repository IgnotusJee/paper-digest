import pytest
import xml.etree.ElementTree as ET
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import date

from src.core.fetcher import PaperRaw, _parse_entry, fetch_arxiv, ATOM_NS


SAMPLE_ENTRY_XML = """<entry xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <id>http://arxiv.org/abs/2506.12345v1</id>
  <title>Test Paper Title</title>
  <summary>Test abstract content.</summary>
  <author><name>Alice</name></author>
  <author><name>Bob</name></author>
  <link href="http://arxiv.org/abs/2506.12345v1" type="text/html"/>
  <link href="http://arxiv.org/pdf/2506.12345v1" title="pdf"/>
  <arxiv:comment>Accepted at OSDI'25</arxiv:comment>
  <arxiv:doi>10.1234/test</arxiv:doi>
  <published>2025-06-15T00:00:00Z</published>
  <category term="cs.DC"/>
  <category term="cs.OS"/>
</entry>"""


class TestParseEntry:
    def test_basic_fields(self):
        entry = ET.fromstring(SAMPLE_ENTRY_XML)
        raw = _parse_entry(entry)
        assert raw is not None
        assert raw.title == "Test Paper Title"
        assert raw.abstract == "Test abstract content."
        assert raw.arxiv_id == "2506.12345v1"
        assert raw.authors == ["Alice", "Bob"]
        assert raw.pdf_url == "http://arxiv.org/pdf/2506.12345v1"
        assert raw.url == "http://arxiv.org/abs/2506.12345v1"
        assert raw.comments == "Accepted at OSDI'25"
        assert raw.doi == "10.1234/test"
        assert raw.published == "2025-06-15"
        assert raw.categories == ["cs.DC", "cs.OS"]

    def test_minimal_entry(self):
        xml = """<entry xmlns="http://www.w3.org/2005/Atom">
          <id>http://arxiv.org/abs/9999.00001v1</id>
          <title>Minimal</title>
          <summary>Abstract.</summary>
        </entry>"""
        entry = ET.fromstring(xml)
        raw = _parse_entry(entry)
        assert raw is not None
        assert raw.title == "Minimal"
        assert raw.arxiv_id == "9999.00001v1"
        assert raw.authors == []
        assert raw.comments is None
        assert raw.doi is None

    def test_malformed_returns_none(self):
        entry = ET.fromstring("<entry xmlns='http://www.w3.org/2005/Atom'></entry>")
        raw = _parse_entry(entry)
        assert raw is None


class TestFetchArxiv:
    @pytest.mark.asyncio
    async def test_fetch_single_page(self):
        feed_xml = f"""<feed xmlns="http://www.w3.org/2005/Atom">
          {SAMPLE_ENTRY_XML}
        </feed>"""

        mock_response = MagicMock()
        mock_response.text = feed_xml
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()

        results = await fetch_arxiv(["cs.DC"], date(2025, 6, 15), client=mock_client)
        assert len(results) == 1
        assert results[0].arxiv_id == "2506.12345v1"

        params = mock_client.get.call_args.kwargs["params"]
        assert params["search_query"] == (
            "(cat:cs.DC) AND submittedDate:[202506150000 TO 202506152359]"
        )

    @pytest.mark.asyncio
    async def test_fetch_query_groups_categories_and_bounds_date(self):
        feed_xml = '<feed xmlns="http://www.w3.org/2005/Atom"></feed>'

        mock_response = MagicMock()
        mock_response.text = feed_xml
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        await fetch_arxiv(["cs.DC", "cs.OS"], date(2025, 6, 15), client=mock_client)

        params = mock_client.get.call_args.kwargs["params"]
        assert params["search_query"] == (
            "(cat:cs.DC OR cat:cs.OS) AND submittedDate:[202506150000 TO 202506152359]"
        )

    @pytest.mark.asyncio
    async def test_fetch_empty_response(self):
        feed_xml = '<feed xmlns="http://www.w3.org/2005/Atom"></feed>'

        mock_response = MagicMock()
        mock_response.text = feed_xml
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        results = await fetch_arxiv(["cs.DC"], date(2025, 6, 15), client=mock_client)
        assert results == []

    @pytest.mark.asyncio
    async def test_fetch_filters_by_date(self):
        entry_other_date = """<entry xmlns="http://www.w3.org/2005/Atom">
          <id>http://arxiv.org/abs/2506.99999v1</id>
          <title>Other Date Paper</title>
          <summary>Abstract.</summary>
          <published>2025-01-01T00:00:00Z</published>
        </entry>"""
        feed_xml = f"""<feed xmlns="http://www.w3.org/2005/Atom">
          {SAMPLE_ENTRY_XML}
          {entry_other_date}
        </feed>"""

        mock_response = MagicMock()
        mock_response.text = feed_xml
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        results = await fetch_arxiv(["cs.DC"], date(2025, 6, 15), client=mock_client)
        assert len(results) == 1
        assert results[0].arxiv_id == "2506.12345v1"
