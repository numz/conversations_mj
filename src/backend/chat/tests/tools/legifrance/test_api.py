"""Tests for Legifrance API client."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from chat.tools.legifrance.api import LegifranceAPI
from chat.tools.legifrance.exceptions import (
    LegifranceAuthError,
    LegifranceClientError,
    LegifranceConnectionError,
    LegifranceRateLimitError,
    LegifranceServerError,
    LegifranceTimeoutError,
)

LEGIFRANCE_BASE_URL = "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app"
LEGIFRANCE_OAUTH_URL = "https://oauth.piste.gouv.fr/api/oauth/token"


class TestLegifranceAPIInit:
    """Test LegifranceAPI initialization."""

    def test_init_with_defaults(self, legifrance_settings):
        """Test API client initializes with settings."""
        client = LegifranceAPI()
        assert client.base_url == legifrance_settings.LEGIFRANCE_API_BASE_URL
        assert client.token == legifrance_settings.LEGIFRANCE_API_TOKEN

    def test_init_with_token(self, legifrance_settings):
        """Test API client uses existing token."""
        legifrance_settings.LEGIFRANCE_API_TOKEN = "preset_token"
        client = LegifranceAPI()
        assert client.token == "preset_token"


class TestCleanText:
    """Test clean_text static method."""

    def test_clean_text_empty(self):
        """Test clean_text with empty input."""
        assert LegifranceAPI.clean_text("") == ""
        assert LegifranceAPI.clean_text(None) == ""

    def test_clean_text_html_tags(self):
        """Test clean_text removes HTML tags."""
        html = "<p>Hello <strong>world</strong></p>"
        assert "Hello" in LegifranceAPI.clean_text(html)
        assert "world" in LegifranceAPI.clean_text(html)
        assert "<" not in LegifranceAPI.clean_text(html)

    def test_clean_text_entities(self):
        """Test clean_text unescapes HTML entities."""
        text = "Hello&nbsp;world &amp; friends"
        result = LegifranceAPI.clean_text(text)
        assert "Hello world" in result
        assert "& friends" in result

    def test_clean_text_non_string(self):
        """Test clean_text handles non-string input."""
        result = LegifranceAPI.clean_text({"key": "value"})
        assert isinstance(result, str)


class TestAuthentication:
    """Test authentication methods."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_authenticate_success(self, sample_oauth_response):
        """Test successful authentication."""
        respx.post(LEGIFRANCE_OAUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_oauth_response)
        )

        client = LegifranceAPI()
        client.token = ""  # Force re-authentication
        await client._authenticate()

        assert client.token == "new_test_token"

    @pytest.mark.asyncio
    async def test_authenticate_missing_credentials(self, legifrance_settings):
        """Test authentication fails with missing credentials."""
        legifrance_settings.LEGIFRANCE_CLIENT_ID = ""
        legifrance_settings.LEGIFRANCE_CLIENT_SECRET = ""

        client = LegifranceAPI()
        client.token = ""

        with pytest.raises(LegifranceAuthError):
            await client._authenticate()

    @pytest.mark.asyncio
    @respx.mock
    async def test_authenticate_401_error(self):
        """Test authentication handles 401 error."""
        respx.post(LEGIFRANCE_OAUTH_URL).mock(return_value=httpx.Response(401, text="Unauthorized"))

        client = LegifranceAPI()
        client.token = ""

        with pytest.raises(LegifranceAuthError):
            await client._authenticate()


class TestSearch:
    """Test search method."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_success(self, sample_search_results):
        """Test successful search."""
        respx.post(f"{LEGIFRANCE_BASE_URL}/search").mock(
            return_value=httpx.Response(200, json={"results": sample_search_results})
        )

        client = LegifranceAPI()
        results = await client.search(
            criteres=[{"typeChamp": "ALL", "criteres": []}], filtres=[], fond="CODE_DATE"
        )

        assert len(results) == 1
        assert results[0]["id"] == "LEGIARTI000006417749"

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_empty_results(self):
        """Test search with no results."""
        respx.post(f"{LEGIFRANCE_BASE_URL}/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )

        client = LegifranceAPI()
        results = await client.search(criteres=[], filtres=[], fond="CODE_DATE")

        assert results == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_rate_limit(self):
        """Test search handles rate limit error."""
        respx.post(f"{LEGIFRANCE_BASE_URL}/search").mock(
            return_value=httpx.Response(429, text="Rate limit exceeded")
        )

        client = LegifranceAPI()

        with pytest.raises(LegifranceRateLimitError):
            await client.search(criteres=[], filtres=[], fond="CODE_DATE")

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_server_error(self):
        """Test search handles server error."""
        respx.post(f"{LEGIFRANCE_BASE_URL}/search").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        client = LegifranceAPI()

        with pytest.raises(LegifranceServerError):
            await client.search(criteres=[], filtres=[], fond="CODE_DATE")

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_client_error(self):
        """Test search handles client error."""
        respx.post(f"{LEGIFRANCE_BASE_URL}/search").mock(
            return_value=httpx.Response(400, text="Bad Request")
        )

        client = LegifranceAPI()

        with pytest.raises(LegifranceClientError):
            await client.search(criteres=[], filtres=[], fond="CODE_DATE")

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_timeout(self):
        """Test search handles timeout."""
        respx.post(f"{LEGIFRANCE_BASE_URL}/search").mock(
            side_effect=httpx.TimeoutException("Request timed out")
        )

        client = LegifranceAPI()

        with pytest.raises(LegifranceTimeoutError):
            await client.search(criteres=[], filtres=[], fond="CODE_DATE")

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_connection_error(self):
        """Test search handles connection error."""
        respx.post(f"{LEGIFRANCE_BASE_URL}/search").mock(
            side_effect=httpx.ConnectError("Connection failed")
        )

        client = LegifranceAPI()

        with pytest.raises(LegifranceConnectionError):
            await client.search(criteres=[], filtres=[], fond="CODE_DATE")


class TestGetDocument:
    """Test get_document method."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_document_legiarti(self, sample_document_response):
        """Test fetching LEGIARTI document."""
        respx.post(f"{LEGIFRANCE_BASE_URL}/consult/getArticle").mock(
            return_value=httpx.Response(200, json=sample_document_response)
        )

        client = LegifranceAPI()
        result = await client.get_document("LEGIARTI000032041571")

        assert result is not None
        assert result["article"]["id"] == "LEGIARTI000032041571"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_document_juritext(self):
        """Test fetching JURITEXT document uses juri endpoint."""
        respx.post(f"{LEGIFRANCE_BASE_URL}/consult/juri").mock(
            return_value=httpx.Response(200, json={"text": {"id": "JURITEXT000001"}})
        )

        client = LegifranceAPI()
        result = await client.get_document("JURITEXT000001")

        assert result is not None

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_document_not_found(self):
        """Test get_document returns None for 404."""
        respx.post(f"{LEGIFRANCE_BASE_URL}/consult/getArticle").mock(
            return_value=httpx.Response(404, text="Not found")
        )

        client = LegifranceAPI()
        result = await client.get_document("LEGIARTI999999")

        assert result is None


class TestListCodes:
    """Test list_codes method."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_codes_success(self, sample_code_list_results):
        """Test listing codes successfully."""
        respx.post(f"{LEGIFRANCE_BASE_URL}/list/code").mock(
            return_value=httpx.Response(200, json={"results": sample_code_list_results})
        )

        client = LegifranceAPI()
        results = await client.list_codes()

        assert len(results) == 2
        assert results[0]["title"] == "Code civil"

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_codes_with_filter(self, sample_code_list_results):
        """Test listing codes with name filter."""
        respx.post(f"{LEGIFRANCE_BASE_URL}/list/code").mock(
            return_value=httpx.Response(200, json={"results": [sample_code_list_results[0]]})
        )

        client = LegifranceAPI()
        results = await client.list_codes(code_name="civil")

        assert len(results) == 1


class TestRetryLogic:
    """Test retry logic for transient errors."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_retry_on_421(self, sample_search_results):
        """Test retry on 421 Misdirected Request."""
        # First request returns 421, second succeeds
        respx.post(f"{LEGIFRANCE_BASE_URL}/search").mock(
            side_effect=[
                httpx.Response(421, text="Misdirected Request"),
                httpx.Response(200, json={"results": sample_search_results}),
            ]
        )

        client = LegifranceAPI()
        results = await client.search(criteres=[], filtres=[], fond="CODE_DATE")

        assert len(results) == 1
        assert respx.calls.call_count == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_refresh_on_401(self, sample_oauth_response, sample_search_results):
        """Test token refresh on 401 during search."""
        # First search returns 401, then auth succeeds, then search succeeds
        respx.post(f"{LEGIFRANCE_BASE_URL}/search").mock(
            side_effect=[
                httpx.Response(401, text="Unauthorized"),
                httpx.Response(200, json={"results": sample_search_results}),
            ]
        )
        respx.post(LEGIFRANCE_OAUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_oauth_response)
        )

        client = LegifranceAPI()
        results = await client.search(criteres=[], filtres=[], fond="CODE_DATE")

        assert len(results) == 1


class TestTokenCaching:
    """Test OAuth token caching functionality."""

    def test_get_cached_token_empty(self):
        """Test getting token from empty cache returns None."""
        from django.core.cache import cache

        cache.delete("legifrance_oauth_token")

        client = LegifranceAPI()
        client.token = ""
        result = client._get_cached_token()

        assert result is None

    def test_set_and_get_cached_token(self):
        """Test setting and getting token from cache."""
        from django.core.cache import cache

        cache.delete("legifrance_oauth_token")

        client = LegifranceAPI()
        client._set_cached_token("test_cached_token", ttl=60)

        cached = client._get_cached_token()
        assert cached == "test_cached_token"

        # Cleanup
        cache.delete("legifrance_oauth_token")

    def test_invalidate_token_cache(self):
        """Test invalidating token cache."""
        from django.core.cache import cache

        client = LegifranceAPI()
        client.token = "existing_token"
        client._set_cached_token("cached_token", ttl=60)

        client._invalidate_token_cache()

        assert client.token == ""
        assert client._get_cached_token() is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_authenticate_stores_token_in_cache(self, sample_oauth_response):
        """Test that authentication stores token in cache."""
        from django.core.cache import cache

        cache.delete("legifrance_oauth_token")

        respx.post(LEGIFRANCE_OAUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_oauth_response)
        )

        client = LegifranceAPI()
        client.token = ""
        await client._authenticate()

        # Token should be stored in cache
        cached_token = cache.get("legifrance_oauth_token")
        assert cached_token == "new_test_token"

        # Cleanup
        cache.delete("legifrance_oauth_token")

    @pytest.mark.asyncio
    @respx.mock
    async def test_uses_cached_token_instead_of_authenticating(self, sample_search_results):
        """Test that cached token is used without re-authenticating."""
        from django.core.cache import cache

        # Pre-set token in cache
        cache.set("legifrance_oauth_token", "pre_cached_token", 60)

        respx.post(f"{LEGIFRANCE_BASE_URL}/search").mock(
            return_value=httpx.Response(200, json={"results": sample_search_results})
        )
        # OAuth endpoint should NOT be called
        oauth_mock = respx.post(LEGIFRANCE_OAUTH_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "new_token"})
        )

        client = LegifranceAPI()
        client.token = ""  # Force to check cache
        results = await client.search(criteres=[], filtres=[], fond="CODE_DATE")

        assert len(results) == 1
        assert client.token == "pre_cached_token"
        # OAuth should not have been called
        assert oauth_mock.call_count == 0

        # Cleanup
        cache.delete("legifrance_oauth_token")

    @pytest.mark.asyncio
    @respx.mock
    async def test_401_invalidates_cache_and_refreshes(
        self, sample_oauth_response, sample_search_results
    ):
        """Test that 401 error invalidates cache and refreshes token."""
        from django.core.cache import cache

        # Pre-set an expired/invalid token in cache
        cache.set("legifrance_oauth_token", "expired_token", 60)

        respx.post(f"{LEGIFRANCE_BASE_URL}/search").mock(
            side_effect=[
                httpx.Response(401, text="Token expired"),
                httpx.Response(200, json={"results": sample_search_results}),
            ]
        )
        respx.post(LEGIFRANCE_OAUTH_URL).mock(
            return_value=httpx.Response(200, json=sample_oauth_response)
        )

        client = LegifranceAPI()
        client.token = ""
        results = await client.search(criteres=[], filtres=[], fond="CODE_DATE")

        assert len(results) == 1
        # New token should be in cache
        assert cache.get("legifrance_oauth_token") == "new_test_token"

        # Cleanup
        cache.delete("legifrance_oauth_token")
