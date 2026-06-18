import logging
import re

from ..config import APP_CONFIG

logger = logging.getLogger(__name__)

_VENUE_PATTERNS: dict[tuple[str, ...], list[tuple[str, re.Pattern]]] = {}


def _build_patterns(venues: list[str]) -> list[tuple[str, re.Pattern]]:
    patterns = []
    for venue in venues:
        escaped = re.escape(venue)
        p1 = re.compile(
            rf"(?:accepted|to appear|published)\s+(?:at|in|for)\s+{escaped}\b",
            re.IGNORECASE,
        )
        patterns.append((venue, p1))
        p2 = re.compile(rf"{escaped}\s*'?\s*(\d{{2,4}})", re.IGNORECASE)
        patterns.append((venue, p2))
    return patterns


def extract_venue_hint(comments: str | None, app_config: dict | None = None) -> str | None:
    if not comments:
        return None

    app_config = app_config or APP_CONFIG
    venues = app_config.get("sources", {}).get("buckets", [{}])[0].get("venues", [])
    cache_key = tuple(venues)
    patterns = _VENUE_PATTERNS.get(cache_key)
    if patterns is None:
        patterns = _build_patterns(venues)
        _VENUE_PATTERNS[cache_key] = patterns

    for venue, pattern in patterns:
        if pattern.search(comments):
            logger.debug("venue_hint matched: %s", venue)
            return venue

    return None
