"""Tests for the shared fuzzy-match helper used by category resolution and
entity-linking search."""
from scripts.matching import find_best_match


def test_exact_match_case_insensitive():
    candidates = [{"id": "1", "title": "Characters"}, {"id": "2", "title": "Places"}]
    result = find_best_match("characters", candidates, key="title")
    assert result is not None
    assert result["id"] == "1"


def test_close_match_typo():
    candidates = [{"id": "1", "title": "Adventuring Guild"}, {"id": "2", "title": "Places"}]
    result = find_best_match("Adventuring Gild", candidates, key="title")
    assert result is not None
    assert result["id"] == "1"


def test_no_match_returns_none():
    candidates = [{"id": "1", "title": "Characters"}, {"id": "2", "title": "Places"}]
    result = find_best_match("Completely Unrelated Thing", candidates, key="title")
    assert result is None


def test_empty_candidates_returns_none():
    assert find_best_match("Anything", [], key="title") is None
