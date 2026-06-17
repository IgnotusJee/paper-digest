import pytest
from src.core.venue_hint import extract_venue_hint


class TestExtractVenueHint:
    def test_accepted_at_osdi(self):
        assert extract_venue_hint("Accepted at OSDI'25") == "OSDI"

    def test_to_appear_sosp(self):
        assert extract_venue_hint("To appear in SOSP 2025") == "SOSP"

    def test_published_at_vldb(self):
        assert extract_venue_hint("Published at VLDB 2026") == "VLDB"

    def test_no_match(self):
        assert extract_venue_hint("We present a new method") is None

    def test_none_input(self):
        assert extract_venue_hint(None) is None

    def test_empty_string(self):
        assert extract_venue_hint("") is None

    def test_case_insensitive(self):
        assert extract_venue_hint("accepted at osdi") == "OSDI"

    def test_venue_with_year_suffix(self):
        assert extract_venue_hint("OSDI'25") == "OSDI"

    def test_venue_with_space_year(self):
        assert extract_venue_hint("OSDI 2025") == "OSDI"

    def test_first_match_wins(self):
        comments = "Accepted at OSDI'25. Also related to SOSP."
        result = extract_venue_hint(comments)
        assert result == "OSDI"
