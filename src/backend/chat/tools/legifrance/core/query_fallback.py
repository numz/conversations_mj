"""Automatic query simplification and fallback retry for Legifrance searches.

When a search returns 0 results, this module provides strategies to retry
with a simplified query before giving up.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# French stop words to strip from queries
_STOP_WORDS = frozenset(
    "le la les un une des du de d l au aux en et ou "
    "qui que qu est ce sa son ses dans par pour sur avec "
    "cette ces ne pas plus".split()
)


def simplify_query(query: str, max_words: int = 3) -> str | None:
    """Simplify a query by removing stop words and truncating.

    Returns None if the simplified query is identical to the original
    or too short to be useful.
    """
    words = re.findall(r"[\w'-]+", query.lower(), re.UNICODE)
    # Remove stop words
    meaningful = [w for w in words if w not in _STOP_WORDS and len(w) > 1]
    if not meaningful:
        return None
    simplified = " ".join(meaningful[:max_words])
    # Only return if actually different and non-trivial
    if simplified.lower().strip() == query.lower().strip():
        return None
    if len(simplified) < 2:
        return None
    return simplified


def extract_law_number(query: str) -> str | None:
    """Extract a law/decree number like '2019-1141' from a query."""
    m = re.search(r"\b(\d{4}[-–]\d+)\b", query)
    return m.group(1).replace("–", "-") if m else None


def build_law_query(number: str) -> str:
    """Build a search query for a law number."""
    return f"loi {number}"
