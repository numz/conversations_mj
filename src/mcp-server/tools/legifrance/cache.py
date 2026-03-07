"""Caching utilities for Legifrance API responses.

This module provides caching for Legifrance API responses to:
- Reduce API calls and avoid rate limiting
- Improve response times for frequently accessed data
- Cache stable content like legal codes and articles

Uses a simple in-memory dict with TTL (no Django dependency).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

# Type variable for cached data
T = TypeVar("T")

# =============================================================================
# In-memory Cache Store
# =============================================================================

# Structure: {key: (value, expiry_timestamp)}
_cache_store: dict[str, tuple[Any, float]] = {}


# =============================================================================
# Cache Configuration
# =============================================================================

# Cache key prefixes
CACHE_PREFIX = "legifrance"
CACHE_KEY_CODES_LIST = f"{CACHE_PREFIX}:codes_list"
CACHE_KEY_DOCUMENT = f"{CACHE_PREFIX}:doc"
CACHE_KEY_SEARCH = f"{CACHE_PREFIX}:search"

# Default TTLs (in seconds)
DEFAULT_TTL_CODES_LIST = 86400  # 24 hours - code list rarely changes
DEFAULT_TTL_DOCUMENT = 3600  # 1 hour - articles are stable
DEFAULT_TTL_SEARCH = 300  # 5 minutes - search results can change


# Settings-based TTL overrides
def get_cache_ttl(cache_type: str) -> int:
    """Get cache TTL for a given cache type, with env override."""
    # Allow env-based override via LEGIFRANCE_CACHE_TTL_<TYPE> (e.g. LEGIFRANCE_CACHE_TTL_DOCUMENT)
    env_key = f"LEGIFRANCE_CACHE_TTL_{cache_type.upper()}"
    env_val = os.environ.get(env_key)
    if env_val is not None:
        try:
            return int(env_val)
        except ValueError:
            pass

    defaults = {
        "codes_list": DEFAULT_TTL_CODES_LIST,
        "document": DEFAULT_TTL_DOCUMENT,
        "search": DEFAULT_TTL_SEARCH,
    }

    return defaults.get(cache_type, 300)


def is_cache_enabled() -> bool:
    """Check if Legifrance response caching is enabled."""
    return os.environ.get("LEGIFRANCE_CACHE_ENABLED", "true").lower() != "false"


# =============================================================================
# Cache Key Generation
# =============================================================================

def _generate_hash(data: Any) -> str:
    """Generate a short hash from data for cache key."""
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.md5(serialized.encode()).hexdigest()[:12]


def get_codes_list_cache_key(code_name: str = "", states: list[str] | None = None) -> str:
    """Generate cache key for codes list request."""
    params = {
        "code_name": code_name.lower().strip(),
        "states": sorted(states) if states else ["VIGUEUR"],
    }
    return f"{CACHE_KEY_CODES_LIST}:{_generate_hash(params)}"


def get_document_cache_key(article_id: str) -> str:
    """Generate cache key for document request."""
    return f"{CACHE_KEY_DOCUMENT}:{article_id.upper()}"


def get_search_cache_key(
    fond: str,
    criteres: list[dict[str, Any]],
    filtres: list[dict[str, Any]],
    sort: str,
    page_number: int = 1,
) -> str:
    """Generate cache key for search request."""
    params = {
        "fond": fond,
        "criteres": criteres,
        "filtres": filtres,
        "sort": sort,
        "page": page_number,
    }
    return f"{CACHE_KEY_SEARCH}:{fond}:{_generate_hash(params)}"


# =============================================================================
# Cache Operations
# =============================================================================

def _cleanup_expired() -> None:
    """Remove expired entries (called lazily)."""
    now = time.time()
    expired = [k for k, (_, exp) in _cache_store.items() if exp <= now]
    for k in expired:
        del _cache_store[k]


def get_cached(key: str) -> Any | None:
    """Get value from cache.

    Args:
        key: Cache key.

    Returns:
        Cached value or None if not found/expired.
    """
    if not is_cache_enabled():
        return None

    try:
        entry = _cache_store.get(key)
        if entry is None:
            return None
        value, expiry = entry
        if time.time() >= expiry:
            del _cache_store[key]
            return None
        logger.debug("Cache HIT for key: %s", key)
        return value
    except Exception as e:
        logger.warning("Cache GET error for key %s: %s", key, e)
        return None


def set_cached(key: str, value: Any, ttl: int | None = None) -> bool:
    """Set value in cache.

    Args:
        key: Cache key.
        value: Value to cache.
        ttl: Time-to-live in seconds (optional, defaults to 300s).

    Returns:
        True if cached successfully, False otherwise.
    """
    if not is_cache_enabled():
        return False

    if value is None:
        return False

    try:
        effective_ttl = ttl if ttl is not None else 300
        expiry = time.time() + effective_ttl
        _cache_store[key] = (value, expiry)
        logger.debug("Cache SET for key: %s (TTL: %s)", key, effective_ttl)
        return True
    except Exception as e:
        logger.warning("Cache SET error for key %s: %s", key, e)
        return False


def delete_cached(key: str) -> bool:
    """Delete value from cache.

    Args:
        key: Cache key.

    Returns:
        True if deleted, False otherwise.
    """
    try:
        _cache_store.pop(key, None)
        logger.debug("Cache DELETE for key: %s", key)
        return True
    except Exception as e:
        logger.warning("Cache DELETE error for key %s: %s", key, e)
        return False


def invalidate_codes_cache() -> None:
    """Invalidate all cached codes lists."""
    try:
        keys_to_delete = [k for k in _cache_store if k.startswith(CACHE_KEY_CODES_LIST)]
        for k in keys_to_delete:
            del _cache_store[k]
        logger.info("Invalidated codes list cache (%d entries)", len(keys_to_delete))
    except Exception as e:
        logger.warning("Error invalidating codes cache: %s", e)


def invalidate_document_cache(article_id: str) -> None:
    """Invalidate cached document.

    Args:
        article_id: The document ID to invalidate.
    """
    key = get_document_cache_key(article_id)
    delete_cached(key)
    logger.info("Invalidated document cache for: %s", article_id)


# =============================================================================
# Cache Statistics (for monitoring)
# =============================================================================

class CacheStats:
    """Simple cache statistics tracker."""

    _hits: int = 0
    _misses: int = 0

    @classmethod
    def record_hit(cls) -> None:
        """Record a cache hit."""
        cls._hits += 1

    @classmethod
    def record_miss(cls) -> None:
        """Record a cache miss."""
        cls._misses += 1

    @classmethod
    def get_stats(cls) -> dict[str, Any]:
        """Get cache statistics."""
        total = cls._hits + cls._misses
        hit_rate = (cls._hits / total * 100) if total > 0 else 0
        return {
            "hits": cls._hits,
            "misses": cls._misses,
            "total": total,
            "hit_rate_percent": round(hit_rate, 2),
        }

    @classmethod
    def reset(cls) -> None:
        """Reset statistics."""
        cls._hits = 0
        cls._misses = 0
