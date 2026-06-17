import logging
import re

from ..config import APP_CONFIG

logger = logging.getLogger(__name__)

_VENUE_PATTERNS: list[tuple[str, re.Pattern]] = []


def _build_patterns() -> list[tuple[str, re.Pattern]]:
    venues = APP_CONFIG.get("sources", {}).get("buckets", [{}])[0].get("venues", [])
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


def extract_venue_hint(comments: str | None) -> str | None:
    if not comments:
        return None

    if not _VENUE_PATTERNS:
        _VENUE_PATTERNS.extend(_build_patterns())

    for venue, pattern in _VENUE_PATTERNS:
        if pattern.search(comments):
            logger.debug("venue_hint matched: %s", venue)
            return venue

    return None
