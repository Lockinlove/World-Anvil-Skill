"""Fuzzy-match helper shared by category resolution and entity-linking
search. Uses stdlib difflib only — no extra dependency."""
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

CLOSE_MATCH_CUTOFF = 0.75


def find_best_match(query: str, candidates: List[Dict[str, Any]], key: str) -> Optional[Dict[str, Any]]:
    """Return the candidate dict whose `key` field best matches `query`.

    Tries an exact case-insensitive match first, then falls back to the
    closest fuzzy match above CLOSE_MATCH_CUTOFF. Returns None if nothing
    clears the bar (caller must then ask the user rather than guessing).
    """
    if not candidates:
        return None

    query_lower = query.strip().lower()
    for candidate in candidates:
        if str(candidate.get(key, "")).strip().lower() == query_lower:
            return candidate

    best_candidate = None
    best_ratio = 0.0
    for candidate in candidates:
        value = str(candidate.get(key, "")).strip().lower()
        ratio = SequenceMatcher(None, query_lower, value).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_candidate = candidate

    if best_ratio >= CLOSE_MATCH_CUTOFF:
        return best_candidate
    return None
