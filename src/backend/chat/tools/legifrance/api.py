"""Legifrance API Client."""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
import re
from typing import Any
from urllib.parse import urlparse

from django.conf import settings
from django.core.cache import cache

import httpx
from pydantic import ValidationError

from .cache import (
    CacheStats,
    get_cache_ttl,
    get_cached,
    get_codes_list_cache_key,
    get_document_cache_key,
    get_search_cache_key,
    set_cached,
)
from .constants import (
    DEFAULT_API_BASE_URL,
    DEFAULT_OAUTH_URL,
    DEFAULT_OPERATOR,
    DEFAULT_PAGE_NUMBER,
    DEFAULT_PAGE_SIZE,
    DEFAULT_PAGINATION_TYPE,
    ENDPOINTS,
    FACET_NOM_CODE,
    FOND_CODE_DATE,
    LEGAL_STATUS_VIGUEUR,
    PAGINATION_TYPE_ARTICLE,
    SEARCH_FIELD_ALL,
    SEARCH_FIELD_NUM_ARTICLE,
    SEARCH_TYPE_EXACTE,
    SORT_PERTINENCE,
    SORT_TITLE_ASC,
)
from .core.schemas import (
    CodeListResponse,
    GenericDocumentResponse,
    OAuthResponse,
    SearchResponse,
)
from .core.text_utils import clean_text
from .exceptions import (
    LegifranceAuthError,
    LegifranceClientError,
    LegifranceConnectionError,
    LegifranceParseError,
    LegifranceRateLimitError,
    LegifranceServerError,
    LegifranceTimeoutError,
)
from .logging_utils import (
    log_api_response,
    metrics,
    slog,
    track_request,
)

logger = logging.getLogger(__name__)

# Default timeout configuration
DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=30.0, pool=30.0)

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 0.5

# Token cache configuration
CACHE_TOKEN_KEY = "legifrance_oauth_token"
CACHE_TOKEN_TTL = 3500  # seconds (token expires in 3600s, refresh 100s before)


class LegifranceAPI:
    """Client for the Legifrance API."""

    def __init__(self) -> None:
        """Initialize the Legifrance API client."""
        self.base_url = getattr(settings, "LEGIFRANCE_API_BASE_URL", DEFAULT_API_BASE_URL)
        self.oauth_url = getattr(settings, "LEGIFRANCE_OAUTH_URL", DEFAULT_OAUTH_URL)
        self.client_id = getattr(settings, "LEGIFRANCE_CLIENT_ID", "")
        self.client_secret = getattr(settings, "LEGIFRANCE_CLIENT_SECRET", "")
        self.ssl_verify = getattr(settings, "LEGIFRANCE_SSL_VERIFY", True)
        self.oauth_host = getattr(settings, "LEGIFRANCE_OAUTH_HOST", "")
        self.api_host = getattr(settings, "LEGIFRANCE_API_HOST", "")

        # Try static token first, then check cache, then fetch dynamic one
        self.token = getattr(settings, "LEGIFRANCE_API_TOKEN", "")

        # Endpoints map
        self.endpoints = ENDPOINTS

    def _get_cached_token(self) -> str | None:
        """Get token from cache if available."""
        token = cache.get(CACHE_TOKEN_KEY)
        return str(token) if token else None

    def _set_cached_token(self, token: str, ttl: int = CACHE_TOKEN_TTL) -> None:
        """Store token in cache."""
        cache.set(CACHE_TOKEN_KEY, token, ttl)
        logger.debug("Stored OAuth token in cache (TTL: %ds)", ttl)

    def _invalidate_token_cache(self) -> None:
        """Remove token from cache (e.g., on 401 error)."""
        cache.delete(CACHE_TOKEN_KEY)
        self.token = ""
        logger.debug("Invalidated OAuth token cache")

    @staticmethod
    def clean_text(text: Any) -> str:
        """Strip HTML tags and unescape entities.

        This is a wrapper around core.text_utils.clean_text for backwards
        compatibility. New code should import clean_text directly from
        chat.tools.legifrance.core.text_utils.
        """
        return clean_text(text)

    def _raise_for_status(self, response: httpx.Response) -> None:
        """Raise appropriate exception based on HTTP status code."""
        status_code = response.status_code

        if status_code < 400:
            return

        try:
            error_body = response.text[:500]
        except Exception:
            error_body = "Unable to read response body"

        if status_code == 401:
            raise LegifranceAuthError(
                f"Authentication failed: {error_body}", status_code=status_code
            )
        elif status_code == 429:
            raise LegifranceRateLimitError(
                f"Rate limit exceeded: {error_body}", status_code=status_code
            )
        elif status_code == 421 or status_code >= 500:
            raise LegifranceServerError(
                f"Server error ({status_code}): {error_body}", status_code=status_code
            )
        else:
            raise LegifranceClientError(
                f"Client error ({status_code}): {error_body}", status_code=status_code
            )

    async def _request_with_retry(
        self, client: httpx.AsyncClient, method: str, url: str, **kwargs: Any
    ) -> httpx.Response:
        """Execute HTTP request with retry logic for transient errors."""
        # Log the request payload for debugging
        if "json" in kwargs:
            logger.debug("Legifrance request to %s: %s", url, json.dumps(kwargs["json"], indent=2))

        last_exception: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                if method.lower() == "post":
                    resp = await client.post(url, **kwargs)
                else:
                    resp = await client.get(url, **kwargs)

                # Handle 421 Misdirected Request - retry
                if resp.status_code == 421:
                    logger.warning(
                        "Legifrance returned 421 (attempt %d/%d), retrying",
                        attempt + 1,
                        MAX_RETRIES,
                    )
                    await asyncio.sleep(RETRY_BACKOFF_FACTOR * (attempt + 1))
                    continue

                # Log response for debugging
                if resp.status_code < 400:
                    try:
                        logger.debug("Legifrance response: %s", json.dumps(resp.json(), indent=2))
                    except Exception:
                        pass

                return resp

            except httpx.TimeoutException as e:
                last_exception = LegifranceTimeoutError(
                    f"Request timed out (attempt {attempt + 1}/{MAX_RETRIES}): {e}"
                )
                logger.warning(
                    "Legifrance timeout (attempt %d/%d): %s",
                    attempt + 1,
                    MAX_RETRIES,
                    e,
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_BACKOFF_FACTOR * (attempt + 1))
                    continue
                raise last_exception from e

            except httpx.ConnectError as e:
                last_exception = LegifranceConnectionError(
                    f"Connection failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}"
                )
                logger.warning(
                    "Legifrance connection error (attempt %d/%d): %s",
                    attempt + 1,
                    MAX_RETRIES,
                    e,
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_BACKOFF_FACTOR * (attempt + 1))
                    continue
                raise last_exception from e

        # Should not reach here, but just in case
        raise last_exception or LegifranceServerError("Max retries exceeded")

    async def _authenticate(self) -> None:
        """Fetch a new OAuth2 token using client credentials."""
        if not self.client_id or not self.client_secret:
            logger.error("Missing Client ID or Secret for Legifrance OAuth")
            raise LegifranceAuthError("Missing Client ID or Secret")

        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "openid",
        }

        headers = {}
        # Fix 421 Misdirected Request: Always force Host header to hostname
        if self.oauth_url:
            headers["Host"] = urlparse(self.oauth_url).hostname

        logger.debug(
            "Authenticating to Legifrance at %s with headers: %s",
            self.oauth_url,
            headers,
        )

        try:
            async with httpx.AsyncClient(verify=self.ssl_verify, timeout=DEFAULT_TIMEOUT) as client:
                resp = await self._request_with_retry(
                    client,
                    "post",
                    self.oauth_url,
                    data=payload,
                    headers=headers if headers else None,
                )
                self._raise_for_status(resp)
                data = resp.json()

                # Validate OAuth response with Pydantic
                try:
                    oauth_response = OAuthResponse.model_validate(data)
                    self.token = oauth_response.access_token

                    # Cache the token with appropriate TTL
                    # Use expires_in from response, minus buffer, or default TTL
                    ttl = min(oauth_response.expires_in - 100, CACHE_TOKEN_TTL)
                    if ttl > 0:
                        self._set_cached_token(self.token, ttl)

                except ValidationError as ve:
                    logger.error("Invalid OAuth response format: %s", ve)
                    raise LegifranceAuthError(f"Invalid OAuth response: {ve}") from ve

                logger.info("Successfully refreshed Legifrance API token")
        except (
            LegifranceAuthError,
            LegifranceTimeoutError,
            LegifranceConnectionError,
        ):
            raise
        except Exception as e:
            logger.exception("Legifrance authentication error: %s", e)
            raise LegifranceAuthError(f"Authentication failed: {e}") from e

    async def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests, authenticating if needed."""
        if not self.token:
            # Check cache first
            cached_token = self._get_cached_token()
            if cached_token:
                self.token = cached_token
                logger.debug("Using cached OAuth token")
            else:
                await self._authenticate()

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self.api_host:
            headers["Host"] = self.api_host

        return headers

    async def _execute_request(
        self, method: str, path: str, payload: dict[str, Any], retry_on_auth: bool = True
    ) -> dict[str, Any] | None:
        """Execute an API request with authentication and error handling."""
        url = f"{self.base_url}{path}"

        if not self.token:
            # Check cache first before authenticating
            cached_token = self._get_cached_token()
            if cached_token:
                self.token = cached_token
                logger.debug("Using cached OAuth token for request")
            else:
                await self._authenticate()

        async with httpx.AsyncClient(verify=self.ssl_verify, timeout=DEFAULT_TIMEOUT) as client:
            headers = await self._get_headers()
            resp = await self._request_with_retry(
                client, method, url, json=payload, headers=headers
            )

            # Retry once if unauthorized
            if resp.status_code == 401 and retry_on_auth:
                logger.info("Legifrance token expired, invalidating cache and refreshing")
                self._invalidate_token_cache()
                await self._authenticate()
                headers = await self._get_headers()
                resp = await self._request_with_retry(
                    client, method, url, json=payload, headers=headers
                )

            self._raise_for_status(resp)
            result: dict[str, Any] = resp.json()
            return result

    async def search(
        self,
        criteres: list[dict[str, Any]],
        filtres: list[dict[str, Any]],
        fond: str = "CODE_ETAT",
        sort: str = SORT_PERTINENCE,
        operateur: str = DEFAULT_OPERATOR,
        page_number: int = DEFAULT_PAGE_NUMBER,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> list[dict[str, Any]]:
        """
        Execute a search on Legifrance API.

        Args:
            criteres: List of search criteria (typeChamp, criteres list, operateur).
            filtres: List of additional filters (facette, valeurs).
            fond: The source database (CODE_ETAT, CODE_DATE, JURI, etc.).
            sort: API sort key (e.g. PERTINENCE, DATE_DESC).
            operateur: Global operator (ET/OU).
            page_number: Page number for pagination.
            page_size: Number of results per page.

        Returns:
            List of search results.

        Raises:
            LegifranceAPIError: On API errors.
        """
        with track_request("search", fond=fond, page=page_number) as ctx:
            payload = {
                "fond": fond,
                "recherche": {
                    "champs": criteres,
                    "filtres": filtres or [],
                    "pageNumber": page_number,
                    "pageSize": page_size,
                    "operateur": operateur,
                    "sort": sort,
                    "typePagination": DEFAULT_PAGINATION_TYPE,
                },
            }

            data = await self._execute_request("post", "/search", payload)
            if not data:
                log_api_response("search", ctx.duration_ms, True, result_count=0, fond=fond)
                return []

            # Validate response with Pydantic
            try:
                response = SearchResponse.model_validate(data)
                # Convert Pydantic models back to dicts for downstream compatibility
                results = [r.model_dump(exclude_none=True) for r in response.results]
                log_api_response(
                    "search", ctx.duration_ms, True, result_count=len(results), fond=fond
                )
                return results
            except ValidationError as ve:
                slog.warning(
                    "Search response validation warning (using raw data)", error=str(ve)[:100]
                )
                # Fall back to raw data if validation fails
                raw_results = data.get("results")
                results = list(raw_results) if isinstance(raw_results, list) else []
                log_api_response(
                    "search", ctx.duration_ms, True, result_count=len(results), fond=fond
                )
                return results

    async def get_document(self, article_id: str, use_cache: bool = True) -> dict[str, Any] | None:
        """
        Fetch article or document content by ID.

        Results are cached for 1 hour by default as legal articles are stable.

        Args:
            article_id: The document identifier.
            use_cache: Whether to use caching (default True).

        Returns:
            Document data or None if not found.

        Raises:
            LegifranceAPIError: On API errors.
        """
        with track_request("get_document", article_id=article_id) as ctx:
            # Check cache first
            if use_cache:
                cache_key = get_document_cache_key(article_id)
                cached_result = get_cached(cache_key)
                if cached_result is not None:
                    CacheStats.record_hit()
                    ctx.cache_hit = True
                    log_api_response(
                        "get_document", ctx.duration_ms, True, cache_hit=True, article_id=article_id
                    )
                    return cached_result
                CacheStats.record_miss()

            path = self.endpoints["consult_article"]
            payload: dict[str, Any] = {"id": article_id}

            # Dispatch logic based on ID prefix
            if article_id.startswith("ACCOTEXT"):
                path = self.endpoints["consult_acco"]
                payload = {"id": article_id}
            elif article_id.startswith("CNILTEXT"):
                path = self.endpoints["consult_cnil"]
                payload = {"textId": article_id}
            elif article_id.startswith("JORFTEXT"):
                path = self.endpoints["consult_jorf"]
                payload = {"textCid": article_id}
            elif article_id.startswith("JORFARTI"):
                path = self.endpoints["consult_article"]
                payload = {"id": article_id}
            elif article_id.startswith(("JURITEXT", "CETATEXT", "CONSTEXT", "JUFITEXT")):
                path = self.endpoints["consult_juri"]
                payload = {"textId": article_id}
            elif article_id.startswith("KALITEXT"):
                path = self.endpoints["consult_kali_text"]
                payload = {"id": article_id}
            elif article_id.startswith("KALIARTI"):
                path = self.endpoints["consult_kali_article"]
                payload = {"id": article_id}
            elif article_id.startswith("LEGIARTI"):
                path = self.endpoints["consult_article"]
                payload = {"id": article_id}
            elif article_id.startswith("LEGITEXT"):
                path = self.endpoints["consult_loda"]
                payload = {"textId": article_id, "date": datetime.date.today().isoformat()}
            elif article_id.isdigit() or (len(article_id) < 20 and not article_id.isalpha()):
                path = self.endpoints["consult_circulaire"]
                payload = {"id": article_id}

            try:
                data = await self._execute_request("post", path, payload)
                if not data:
                    log_api_response(
                        "get_document", ctx.duration_ms, True, article_id=article_id, found=False
                    )
                    return None

                # Validate response with Pydantic
                try:
                    response = GenericDocumentResponse.model_validate(data)
                    slog.debug("Document response validated successfully")
                except ValidationError as ve:
                    slog.warning(
                        "Document response validation warning (using raw data)", error=str(ve)[:100]
                    )

                # Cache the result before returning
                if use_cache and data:
                    cache_key = get_document_cache_key(article_id)
                    ttl = get_cache_ttl("document")
                    set_cached(cache_key, data, ttl)

                log_api_response(
                    "get_document", ctx.duration_ms, True, article_id=article_id, found=True
                )
                return data

            except LegifranceClientError as e:
                if e.status_code == 404:
                    log_api_response(
                        "get_document", ctx.duration_ms, True, article_id=article_id, found=False
                    )
                    return None
                raise

    async def get_article_with_id_and_num(self, text_id: str, num: str) -> dict[str, Any] | None:
        """
        Fetch an article by its Code/Text ID and Article Number.

        Args:
            text_id: The Code/Text identifier.
            num: The article number.

        Returns:
            Article data or None if not found.

        Raises:
            LegifranceAPIError: On API errors.
        """
        payload = {"id": text_id, "num": num}

        try:
            return await self._execute_request(
                "post", self.endpoints["consult_article_id_num"], payload
            )
        except LegifranceClientError as e:
            if e.status_code == 404:
                return None
            raise

    async def search_code_article(
        self, code_name: str, article_num: str, use_cache: bool = True
    ) -> list[dict[str, Any]]:
        """
        Specialized search for a specific article number in a Code.

        Results are cached for 1 hour by default as article searches are stable.

        Args:
            code_name: Name of the legal code.
            article_num: Article number to search for.
            use_cache: Whether to use caching (default True).

        Returns:
            List of matching articles.

        Raises:
            LegifranceAPIError: On API errors.
        """
        query = f"{code_name} art. {article_num}"
        with track_request("search_code_article", fond=FOND_CODE_DATE, query=query) as ctx:
            # Check cache first
            if use_cache:
                criteres = [{"code_name": code_name, "article_num": article_num}]
                cache_key = get_search_cache_key(FOND_CODE_DATE, criteres, [], SORT_PERTINENCE, 1)
                cached_result = get_cached(cache_key)
                if cached_result is not None:
                    CacheStats.record_hit()
                    ctx.cache_hit = True
                    log_api_response(
                        "search_code_article",
                        ctx.duration_ms,
                        True,
                        result_count=len(cached_result),
                        cache_hit=True,
                    )
                    return cached_result
                CacheStats.record_miss()

            payload = {
                "fond": FOND_CODE_DATE,
                "recherche": {
                    "champs": [
                        {
                            "typeChamp": SEARCH_FIELD_NUM_ARTICLE,
                            "criteres": [
                                {
                                    "typeRecherche": SEARCH_TYPE_EXACTE,
                                    "valeur": article_num,
                                    "operateur": DEFAULT_OPERATOR,
                                }
                            ],
                            "operateur": DEFAULT_OPERATOR,
                        }
                    ],
                    "filtres": [{"facette": FACET_NOM_CODE, "valeurs": [code_name]}],
                    "pageNumber": 1,
                    "pageSize": 5,
                    "operateur": DEFAULT_OPERATOR,
                    "sort": SORT_PERTINENCE,
                    "typePagination": PAGINATION_TYPE_ARTICLE,
                },
            }

            data = await self._execute_request("post", self.endpoints["search"], payload)
            if not data:
                log_api_response("search_code_article", ctx.duration_ms, True, result_count=0)
                return []

            # Validate response with Pydantic
            try:
                response = SearchResponse.model_validate(data)
                result = [r.model_dump(exclude_none=True) for r in response.results]
            except ValidationError as ve:
                slog.warning(
                    "Code article search validation warning (using raw data)", error=str(ve)[:100]
                )
                raw_results = data.get("results")
                result = list(raw_results) if isinstance(raw_results, list) else []

            # Cache the result
            if use_cache and result:
                criteres = [{"code_name": code_name, "article_num": article_num}]
                cache_key = get_search_cache_key(FOND_CODE_DATE, criteres, [], SORT_PERTINENCE, 1)
                ttl = get_cache_ttl("document")  # Use document TTL for article searches
                set_cached(cache_key, result, ttl)

            log_api_response("search_code_article", ctx.duration_ms, True, result_count=len(result))
            return result

    async def list_codes(
        self, code_name: str = "", states: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        List/Search for codes using the /list/code endpoint.

        Results are cached for 24 hours by default as the code list rarely changes.

        Args:
            code_name: Optional filter by code name.
            states: List of legal states to filter by.

        Returns:
            List of codes.

        Raises:
            LegifranceAPIError: On API errors.
        """
        if states is None:
            states = [LEGAL_STATUS_VIGUEUR]

        with track_request("list_codes", query=code_name or "(all)") as ctx:
            # Check cache first
            cache_key = get_codes_list_cache_key(code_name, states)
            cached_result = get_cached(cache_key)
            if cached_result is not None:
                CacheStats.record_hit()
                ctx.cache_hit = True
                log_api_response(
                    "list_codes",
                    ctx.duration_ms,
                    True,
                    result_count=len(cached_result),
                    cache_hit=True,
                )
                return cached_result

            CacheStats.record_miss()

            payload = {
                "codeName": code_name,
                "pageNumber": 1,
                "pageSize": 150,
                "states": states,
                "sort": SORT_TITLE_ASC,
            }

            data = await self._execute_request("post", ENDPOINTS["list_code_legacy"], payload)
            if not data:
                log_api_response("list_codes", ctx.duration_ms, True, result_count=0)
                return []

            # Validate response with Pydantic
            try:
                response = CodeListResponse.model_validate(data)
                # Convert Pydantic models back to dicts for downstream compatibility
                result = [c.model_dump(exclude_none=True) for c in response.results]
            except ValidationError as ve:
                slog.warning(
                    "Code list response validation warning (using raw data)", error=str(ve)[:100]
                )
                # Fall back to raw data if validation fails
                raw_results = data.get("results")
                result = list(raw_results) if isinstance(raw_results, list) else []

            # Cache the result
            if result:
                ttl = get_cache_ttl("codes_list")
                set_cached(cache_key, result, ttl)

            log_api_response("list_codes", ctx.duration_ms, True, result_count=len(result))
            return result
