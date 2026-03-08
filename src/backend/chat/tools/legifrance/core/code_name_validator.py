"""Validate code_name against the real list of codes from Legifrance.

Loads the list once (cached 24h in Django cache, in-memory for the process),
then provides fast fuzzy matching so the LLM gets an actionable error message
instead of a silent empty result set.
"""

from __future__ import annotations

import logging
import time
import unicodedata
from difflib import SequenceMatcher

from ..api import LegifranceAPI
from ..cache import get_cached, get_codes_list_cache_key, set_cached, get_cache_ttl

logger = logging.getLogger(__name__)

# In-memory cache: list of (normalised_title, original_title)
_CODE_NAMES: list[tuple[str, str]] = []
_CODE_NAMES_TS: float = 0.0  # epoch when loaded
_CODE_NAMES_TTL: int = 86400  # 24h


def _normalise(s: str) -> str:
    """Lower-case, strip accents, collapse whitespace."""
    s = s.lower().strip()
    # Strip accents
    s = "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )
    # Collapse whitespace
    return " ".join(s.split())


async def _load_code_names() -> list[tuple[str, str]]:
    """Fetch the full list of code titles from the API (or Django cache)."""
    global _CODE_NAMES, _CODE_NAMES_TS  # noqa: PLW0603

    # Check in-memory freshness
    if _CODE_NAMES and (time.time() - _CODE_NAMES_TS) < _CODE_NAMES_TTL:
        return _CODE_NAMES

    try:
        client = LegifranceAPI()
        raw_codes = await client.list_codes()  # already uses Django cache internally
        names: list[tuple[str, str]] = []
        for code in raw_codes:
            title = code.get("title") or code.get("titre") or ""
            if title:
                names.append((_normalise(title), title))
        if names:
            _CODE_NAMES = names
            _CODE_NAMES_TS = time.time()
            logger.info("Loaded %d code names for validation", len(names))
        return names
    except Exception:
        logger.warning("Failed to load code names for validation, skipping check")
        return _CODE_NAMES  # return stale cache if any


def _best_matches(
    query: str, codes: list[tuple[str, str]], n: int = 3
) -> list[tuple[str, float]]:
    """Return the *n* best matching original titles with their score."""
    q = _normalise(query)
    scored: list[tuple[str, float]] = []
    for norm, orig in codes:
        # Exact normalised match → perfect score
        if norm == q:
            return [(orig, 1.0)]
        # Substring containment
        if q in norm or norm in q:
            scored.append((orig, 0.85))
            continue
        ratio = SequenceMatcher(None, q, norm).ratio()
        if ratio >= 0.45:
            scored.append((orig, ratio))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:n]


async def validate_code_name(code_name: str) -> str:
    """Validate *code_name* against the real Legifrance code list.

    Returns:
        The exact official title if there is a close-enough match.

    Raises:
        ValueError with a suggestion message if the name is invalid.
    """
    if not code_name or not code_name.strip():
        raise ValueError("Le nom du code ne peut pas être vide.")

    codes = await _load_code_names()
    if not codes:
        # Could not load the list — skip validation silently
        return code_name.strip()

    q = _normalise(code_name)

    # 1. Exact normalised match
    for norm, orig in codes:
        if norm == q:
            return orig  # return the official title

    # 2. Fuzzy
    matches = _best_matches(code_name, codes)
    if matches and matches[0][1] >= 0.75:
        # Close enough — auto-correct
        return matches[0][0]

    # 3. No good match → error with suggestions
    if matches:
        suggestions = ", ".join(f'"{m[0]}"' for m in matches)
        raise ValueError(
            f"Le code \"{code_name}\" n'existe pas sur Légifrance. "
            f"Codes similaires : {suggestions}. "
            "Utilise legifrance_list_codes pour vérifier le nom exact."
        )
    raise ValueError(
        f"Le code \"{code_name}\" n'existe pas sur Légifrance. "
        "Utilise legifrance_list_codes pour vérifier le nom exact."
    )
