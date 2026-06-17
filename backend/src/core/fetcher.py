import asyncio
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, timedelta

import httpx

ARXIV_API = "http://export.arxiv.org/api/query"
ATOM_NS = {
    "a": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}
RATE_LIMIT_SECS = 3.0
PER_PAGE = 100

logger = logging.getLogger(__name__)


@dataclass
class PaperRaw:
    title: str
    authors: list[str]
    abstract: str
    arxiv_id: str
    pdf_url: str
    url: str
    comments: str | None = None
    doi: str | None = None
    published: str | None = None
    categories: list[str] = field(default_factory=list)


def _extract_arxiv_id(id_url: str) -> str:
    return id_url.rsplit("/", 1)[-1]


def _entry_text(entry: ET.Element, path: str) -> str | None:
    el = entry.find(path, ATOM_NS)
    if el is not None and el.text:
        return el.text.strip()
    return None


def _parse_entry(entry: ET.Element) -> PaperRaw | None:
    try:
        title = entry.find("a:title", ATOM_NS).text.strip().replace("\n", " ")
        abstract = entry.find("a:summary", ATOM_NS).text.strip()
        arxiv_id = _extract_arxiv_id(entry.find("a:id", ATOM_NS).text.strip())

        authors = []
        for author_el in entry.findall("a:author", ATOM_NS):
            name_el = author_el.find("a:name", ATOM_NS)
            if name_el is not None and name_el.text:
                authors.append(name_el.text.strip())

        pdf_url = ""
        url = ""
        for link_el in entry.findall("a:link", ATOM_NS):
            href = link_el.get("href", "")
            if link_el.get("title") == "pdf":
                pdf_url = href
            elif link_el.get("type") == "text/html":
                url = href
        if not url:
            url = entry.find("a:id", ATOM_NS).text.strip()

        comments = _entry_text(entry, "arxiv:comment") or _entry_text(entry, "a:comment")
        doi = _entry_text(entry, "arxiv:doi") or _entry_text(entry, "a:doi")

        published_el = entry.find("a:published", ATOM_NS)
        published = published_el.text.strip()[:10] if published_el is not None and published_el.text else None

        categories = []
        for cat_el in entry.findall("a:category", ATOM_NS):
            term = cat_el.get("term")
            if term:
                categories.append(term)

        return PaperRaw(
            title=title,
            authors=authors,
            abstract=abstract,
            arxiv_id=arxiv_id,
            pdf_url=pdf_url,
            url=url,
            comments=comments,
            doi=doi,
            published=published,
            categories=categories,
        )
    except Exception:
        logger.warning("Failed to parse arXiv entry", exc_info=True)
        return None


async def fetch_arxiv(
    categories: list[str],
    fetch_date: date,
    client: httpx.AsyncClient | None = None,
    max_results: int | None = None,
) -> list[PaperRaw]:
    cat_query = " OR ".join(f"cat:{c}" for c in categories)
    submitted_start = fetch_date.strftime("%Y%m%d0000")
    submitted_end = fetch_date.strftime("%Y%m%d2359")
    search_query = (
        f"({cat_query}) AND submittedDate:[{submitted_start} TO {submitted_end}]"
        if cat_query
        else f"submittedDate:[{submitted_start} TO {submitted_end}]"
    )
    date_start = fetch_date.isoformat()
    date_end = (fetch_date + timedelta(days=1)).isoformat()

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=30)

    results: list[PaperRaw] = []
    try:
        offset = 0
        while max_results is None or offset < max_results:
            page_size = PER_PAGE if max_results is None else min(PER_PAGE, max_results - offset)
            params = {
                "search_query": search_query,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
                "start": offset,
                "max_results": page_size,
            }
            try:
                resp = await client.get(ARXIV_API, params=params)
                resp.raise_for_status()
            except httpx.HTTPError:
                logger.warning("arXiv API request failed (offset=%d), retrying once", offset)
                await asyncio.sleep(5)
                try:
                    resp = await client.get(ARXIV_API, params=params)
                    resp.raise_for_status()
                except httpx.HTTPError:
                    logger.error("arXiv API retry failed, aborting fetch")
                    break

            root = ET.fromstring(resp.text)
            entries = root.findall("a:entry", ATOM_NS)
            if not entries:
                break

            for entry in entries:
                raw = _parse_entry(entry)
                if raw is None:
                    continue
                if raw.published and date_start <= raw.published < date_end:
                    results.append(raw)

            if len(entries) < page_size:
                break

            offset += len(entries)
            await asyncio.sleep(RATE_LIMIT_SECS)
    finally:
        if own_client:
            await client.aclose()

    logger.info("Fetched %d papers from arXiv for %s", len(results), fetch_date)
    return results
