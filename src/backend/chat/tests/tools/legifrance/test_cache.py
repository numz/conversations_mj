"""Tests for Legifrance caching utilities."""

from unittest.mock import patch

import pytest

from chat.tools.legifrance.cache import (
    CACHE_PREFIX,
    CacheStats,
    delete_cached,
    get_cache_ttl,
    get_cached,
    get_codes_list_cache_key,
    get_document_cache_key,
    get_search_cache_key,
    invalidate_codes_cache,
    invalidate_document_cache,
    is_cache_enabled,
    set_cached,
)


class TestCacheKeyGeneration:
    """Test cache key generation functions."""

    def test_codes_list_cache_key_empty(self):
        """Test codes list key with no filter."""
        key = get_codes_list_cache_key()
        assert key.startswith(f"{CACHE_PREFIX}:codes_list:")
        assert len(key) > len(f"{CACHE_PREFIX}:codes_list:")

    def test_codes_list_cache_key_with_filter(self):
        """Test codes list key with filter."""
        key1 = get_codes_list_cache_key("civil")
        key2 = get_codes_list_cache_key("pénal")
        assert key1 != key2

    def test_codes_list_cache_key_case_insensitive(self):
        """Test codes list key is case insensitive."""
        key1 = get_codes_list_cache_key("Civil")
        key2 = get_codes_list_cache_key("civil")
        assert key1 == key2

    def test_codes_list_cache_key_with_states(self):
        """Test codes list key with different states."""
        key1 = get_codes_list_cache_key("", ["VIGUEUR"])
        key2 = get_codes_list_cache_key("", ["ABROGE"])
        assert key1 != key2

    def test_document_cache_key(self):
        """Test document cache key generation."""
        key = get_document_cache_key("LEGIARTI000006417749")
        assert key == f"{CACHE_PREFIX}:doc:LEGIARTI000006417749"

    def test_document_cache_key_uppercase(self):
        """Test document cache key is uppercased."""
        key = get_document_cache_key("legiarti000006417749")
        assert "LEGIARTI000006417749" in key

    def test_search_cache_key(self):
        """Test search cache key generation."""
        criteres = [{"typeChamp": "ALL", "valeur": "test"}]
        filtres = [{"facette": "NOM_CODE", "valeurs": ["Code civil"]}]
        key = get_search_cache_key("CODE_DATE", criteres, filtres, "PERTINENCE", 1)
        assert key.startswith(f"{CACHE_PREFIX}:search:CODE_DATE:")

    def test_search_cache_key_different_queries(self):
        """Test search cache keys are different for different queries."""
        key1 = get_search_cache_key("CODE_DATE", [{"v": "query1"}], [], "PERTINENCE", 1)
        key2 = get_search_cache_key("CODE_DATE", [{"v": "query2"}], [], "PERTINENCE", 1)
        assert key1 != key2

    def test_search_cache_key_same_query(self):
        """Test search cache keys are same for same query."""
        criteres = [{"typeChamp": "ALL"}]
        key1 = get_search_cache_key("JURI", criteres, [], "DATE_DESC", 1)
        key2 = get_search_cache_key("JURI", criteres, [], "DATE_DESC", 1)
        assert key1 == key2


class TestCacheOperations:
    """Test cache operations."""

    def test_set_and_get_cached(self):
        """Test setting and getting cached value."""
        from django.core.cache import cache

        cache.clear()

        key = "test_cache_key"
        value = {"data": "test_value"}

        set_cached(key, value, ttl=60)
        result = get_cached(key)

        assert result == value
        cache.delete(key)

    def test_get_cached_returns_none_for_missing(self):
        """Test get_cached returns None for missing key."""
        result = get_cached("nonexistent_key_12345")
        assert result is None

    def test_set_cached_none_value(self):
        """Test set_cached with None value returns False."""
        result = set_cached("test_key", None)
        assert result is False

    def test_delete_cached(self):
        """Test deleting cached value."""
        from django.core.cache import cache

        key = "test_delete_key"
        cache.set(key, "value", 60)

        delete_cached(key)

        assert cache.get(key) is None

    def test_cache_disabled(self, settings):
        """Test cache operations when disabled."""
        settings.LEGIFRANCE_CACHE_ENABLED = False

        assert get_cached("any_key") is None
        assert set_cached("any_key", "value") is False

        # Re-enable for other tests
        settings.LEGIFRANCE_CACHE_ENABLED = True


class TestCacheConfiguration:
    """Test cache configuration."""

    def test_default_ttls(self):
        """Test default TTL values."""
        assert get_cache_ttl("codes_list") == 86400  # 24 hours
        assert get_cache_ttl("document") == 3600  # 1 hour
        assert get_cache_ttl("search") == 300  # 5 minutes

    def test_custom_ttl_from_settings(self, settings):
        """Test TTL override from settings."""
        settings.LEGIFRANCE_CACHE_TTL = {"codes_list": 7200}

        assert get_cache_ttl("codes_list") == 7200
        assert get_cache_ttl("document") == 3600  # Still default

        # Cleanup
        del settings.LEGIFRANCE_CACHE_TTL

    def test_is_cache_enabled_default(self):
        """Test cache is enabled by default."""
        assert is_cache_enabled() is True

    def test_is_cache_enabled_setting(self, settings):
        """Test cache enabled setting."""
        settings.LEGIFRANCE_CACHE_ENABLED = False
        assert is_cache_enabled() is False

        settings.LEGIFRANCE_CACHE_ENABLED = True
        assert is_cache_enabled() is True


class TestCacheInvalidation:
    """Test cache invalidation functions."""

    def test_invalidate_document_cache(self):
        """Test invalidating document cache."""
        from django.core.cache import cache

        article_id = "LEGIARTI000001"
        key = get_document_cache_key(article_id)
        cache.set(key, {"data": "test"}, 60)

        invalidate_document_cache(article_id)

        assert cache.get(key) is None

    def test_invalidate_codes_cache(self):
        """Test invalidating codes cache."""
        from django.core.cache import cache

        # Set some codes in cache
        key = get_codes_list_cache_key()
        cache.set(key, [{"code": "test"}], 60)

        invalidate_codes_cache()

        # Key should be deleted
        assert cache.get(key) is None


class TestCacheStats:
    """Test cache statistics tracking."""

    def test_record_hit(self):
        """Test recording cache hit."""
        CacheStats.reset()
        CacheStats.record_hit()
        CacheStats.record_hit()

        stats = CacheStats.get_stats()
        assert stats["hits"] == 2

    def test_record_miss(self):
        """Test recording cache miss."""
        CacheStats.reset()
        CacheStats.record_miss()

        stats = CacheStats.get_stats()
        assert stats["misses"] == 1

    def test_hit_rate_calculation(self):
        """Test hit rate percentage calculation."""
        CacheStats.reset()
        CacheStats.record_hit()
        CacheStats.record_hit()
        CacheStats.record_hit()
        CacheStats.record_miss()

        stats = CacheStats.get_stats()
        assert stats["total"] == 4
        assert stats["hit_rate_percent"] == 75.0

    def test_hit_rate_zero_total(self):
        """Test hit rate with zero total."""
        CacheStats.reset()

        stats = CacheStats.get_stats()
        assert stats["hit_rate_percent"] == 0

    def test_reset_stats(self):
        """Test resetting statistics."""
        CacheStats.record_hit()
        CacheStats.record_miss()
        CacheStats.reset()

        stats = CacheStats.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0


class TestCacheIntegration:
    """Test cache integration with API methods."""

    @pytest.mark.asyncio
    async def test_list_codes_uses_cache(self, legifrance_settings, sample_code_list_results):
        """Test list_codes uses cache."""
        from unittest.mock import AsyncMock, patch

        from django.core.cache import cache

        cache.clear()

        with patch(
            "chat.tools.legifrance.api.LegifranceAPI._execute_request",
            new_callable=AsyncMock,
        ) as mock_request:
            mock_request.return_value = {"results": sample_code_list_results}

            from chat.tools.legifrance.api import LegifranceAPI

            client = LegifranceAPI()

            # First call - should hit API
            result1 = await client.list_codes()
            assert mock_request.call_count == 1

            # Second call - should use cache
            result2 = await client.list_codes()
            assert mock_request.call_count == 1  # No additional call

            assert result1 == result2

        cache.clear()

    @pytest.mark.asyncio
    async def test_get_document_uses_cache(self, legifrance_settings, sample_document_response):
        """Test get_document uses cache."""
        from unittest.mock import AsyncMock, patch

        from django.core.cache import cache

        cache.clear()

        with patch(
            "chat.tools.legifrance.api.LegifranceAPI._execute_request",
            new_callable=AsyncMock,
        ) as mock_request:
            mock_request.return_value = sample_document_response

            from chat.tools.legifrance.api import LegifranceAPI

            client = LegifranceAPI()
            article_id = "LEGIARTI000032041571"

            # First call - should hit API
            result1 = await client.get_document(article_id)
            assert mock_request.call_count == 1

            # Second call - should use cache
            result2 = await client.get_document(article_id)
            assert mock_request.call_count == 1  # No additional call

            assert result1 == result2

        cache.clear()

    @pytest.mark.asyncio
    async def test_get_document_bypass_cache(self, legifrance_settings, sample_document_response):
        """Test get_document can bypass cache."""
        from unittest.mock import AsyncMock, patch

        from django.core.cache import cache

        cache.clear()

        with patch(
            "chat.tools.legifrance.api.LegifranceAPI._execute_request",
            new_callable=AsyncMock,
        ) as mock_request:
            mock_request.return_value = sample_document_response

            from chat.tools.legifrance.api import LegifranceAPI

            client = LegifranceAPI()
            article_id = "LEGIARTI000032041571"

            # First call with cache
            await client.get_document(article_id, use_cache=True)
            assert mock_request.call_count == 1

            # Second call bypassing cache
            await client.get_document(article_id, use_cache=False)
            assert mock_request.call_count == 2  # Should call API again

        cache.clear()
