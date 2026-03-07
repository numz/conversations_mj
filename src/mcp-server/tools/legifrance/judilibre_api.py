"""Judilibre API Client.

Judilibre is the open data API for French Court of Cassation decisions.
It uses the same PISTE OAuth system as Legifrance but has different endpoints.

Standalone version (no Django dependency). Configuration via environment variables.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, ValidationError

from .cache import (
    CacheStats,
    get_cached,
    get_cache_ttl,
    set_cached,
    delete_cached,
)
from .exceptions import (
    LegifranceAuthError,
    LegifranceClientError,
    LegifranceConnectionError,
    LegifranceRateLimitError,
    LegifranceServerError,
    LegifranceTimeoutError,
)
from .logging_utils import (
    log_api_response,
    slog,
    track_request,
)

logger = logging.getLogger(__name__)

# Default timeout configuration
DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=30.0, pool=30.0)

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 0.5

# Token cache configuration (shared with Legifrance)
CACHE_TOKEN_KEY = "legifrance_oauth_token"
CACHE_TOKEN_TTL = 3500


# --- Pydantic Models for Response Validation ---


class JudilibreHighlights(BaseModel):
    """Highlights from search results."""
    text: list[str] | None = None


class JudilibreSearchResult(BaseModel):
    """A single search result from Judilibre."""
    id: str
    score: float | None = None
    highlights: JudilibreHighlights | None = None
    jurisdiction: str | None = None
    chamber: str | None = None
    number: str | None = None
    numbers: list[str] | None = None
    ecli: str | None = None
    formation: str | None = None
    publication: list[str] | None = None
    decision_date: str | None = None
    solution: str | None = None
    type: str | None = None
    summary: str | None = None
    themes: list[str] | None = None
    files: list[Any] | None = None


class JudilibreSearchResponse(BaseModel):
    """Response from Judilibre search endpoint."""
    page: int
    page_size: int
    total: int
    results: list[JudilibreSearchResult]
    took: int | None = None
    max_score: float | None = None
    next_page: str | None = None
    previous_page: str | None = None


class JudilibreDecision(BaseModel):
    """A full decision from Judilibre."""
    id: str
    source: str | None = None
    text: str | None = None
    chamber: str | None = None
    decision_date: str | None = None
    ecli: str | None = None
    jurisdiction: str | None = None
    number: str | None = None
    numbers: list[str] | None = None
    publication: list[str] | None = None
    solution: str | None = None
    type: str | None = None
    update_date: str | None = None
    summary: str | None = None
    themes: list[str] | None = None
    zones: dict[str, Any] | None = None
    visa: list[dict[str, Any]] | None = None
    rapprochements: list[dict[str, Any]] | None = None
    contested: dict[str, Any] | None = None
    titlesAndSummaries: list[dict[str, Any]] | None = None


class JudilibreTaxonomyResult(BaseModel):
    """Result from taxonomy endpoint."""
    id: str | None = None
    key: str | None = None
    result: dict[str, Any] | None = None
    results: list[dict[str, Any]] | None = None


class JudilibreAPI:
    """Client for the Judilibre API."""

    def __init__(self) -> None:
        """Initialize the Judilibre API client."""
        # Determine if we're using sandbox or production based on OAuth URL
        oauth_url = os.environ.get("LEGIFRANCE_OAUTH_URL", "")

        if "sandbox" in oauth_url:
            self.base_url = "https://sandbox-api.piste.gouv.fr/cassation/judilibre/v1.0"
        else:
            self.base_url = "https://api.piste.gouv.fr/cassation/judilibre/v1.0"

        self.oauth_url = oauth_url
        self.client_id = os.environ.get("LEGIFRANCE_CLIENT_ID", "")
        self.client_secret = os.environ.get("LEGIFRANCE_CLIENT_SECRET", "")
        self.ssl_verify = os.environ.get("LEGIFRANCE_SSL_VERIFY", "true").lower() == "true"

        self.token = ""

    def _get_cached_token(self) -> str | None:
        """Get token from cache if available."""
        token = get_cached(CACHE_TOKEN_KEY)
        return str(token) if token else None

    def _set_cached_token(self, token: str, ttl: int = CACHE_TOKEN_TTL) -> None:
        """Store token in cache."""
        set_cached(CACHE_TOKEN_KEY, token, ttl)
        logger.debug("Stored OAuth token in cache (TTL: %ds)", ttl)

    def _invalidate_token_cache(self) -> None:
        """Remove token from cache."""
        delete_cached(CACHE_TOKEN_KEY)
        self.token = ""
        logger.debug("Invalidated OAuth token cache")

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
        elif status_code >= 500:
            raise LegifranceServerError(
                f"Server error ({status_code}): {error_body}", status_code=status_code
            )
        else:
            raise LegifranceClientError(
                f"Client error ({status_code}): {error_body}", status_code=status_code
            )

    async def _authenticate(self) -> None:
        """Fetch a new OAuth2 token using client credentials."""
        if not self.client_id or not self.client_secret:
            logger.error("Missing Client ID or Secret for Judilibre OAuth")
            raise LegifranceAuthError("Missing Client ID or Secret")

        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "openid",
        }

        headers = {}
        if self.oauth_url:
            headers["Host"] = urlparse(self.oauth_url).hostname

        logger.debug("Authenticating to Judilibre at %s", self.oauth_url)

        try:
            async with httpx.AsyncClient(
                verify=self.ssl_verify, timeout=DEFAULT_TIMEOUT
            ) as client:
                resp = await client.post(
                    self.oauth_url,
                    data=payload,
                    headers=headers if headers else None,
                )
                self._raise_for_status(resp)
                data = resp.json()

                self.token = data.get("access_token", "")
                expires_in = data.get("expires_in", 3600)

                ttl = min(expires_in - 100, CACHE_TOKEN_TTL)
                if ttl > 0:
                    self._set_cached_token(self.token, ttl)

                logger.info("Successfully obtained Judilibre API token")

        except (LegifranceAuthError, LegifranceTimeoutError, LegifranceConnectionError):
            raise
        except Exception as e:
            logger.exception("Judilibre authentication error: %s", e)
            raise LegifranceAuthError(f"Authentication failed: {e}") from e

    async def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests, authenticating if needed."""
        if not self.token:
            cached_token = self._get_cached_token()
            if cached_token:
                self.token = cached_token
                logger.debug("Using cached OAuth token for Judilibre")
            else:
                await self._authenticate()

        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }

    async def _execute_get(
        self, endpoint: str, params: dict[str, Any] | None = None, retry_on_auth: bool = True
    ) -> dict[str, Any] | None:
        """Execute a GET request to the Judilibre API."""
        url = f"{self.base_url}{endpoint}"

        if not self.token:
            cached_token = self._get_cached_token()
            if cached_token:
                self.token = cached_token
            else:
                await self._authenticate()

        async with httpx.AsyncClient(
            verify=self.ssl_verify, timeout=DEFAULT_TIMEOUT
        ) as client:
            headers = await self._get_headers()

            logger.debug("Judilibre GET %s params=%s", url, params)

            resp = await client.get(url, params=params or {}, headers=headers)

            # Retry once if unauthorized
            if resp.status_code == 401 and retry_on_auth:
                logger.info("Judilibre token expired, refreshing")
                self._invalidate_token_cache()
                await self._authenticate()
                headers = await self._get_headers()
                resp = await client.get(url, params=params or {}, headers=headers)

            self._raise_for_status(resp)
            result: dict[str, Any] = resp.json()
            return result

    async def search(
        self,
        query: str,
        jurisdiction: str | None = None,
        chamber: str | None = None,
        formation: str | None = None,
        publication: str | None = None,
        solution: str | None = None,
        type_decision: str | None = None,
        theme: str | None = None,
        date_start: str | None = None,
        date_end: str | None = None,
        operator: str = "or",
        sort: str = "score",
        order: str = "desc",
        page: int = 0,
        page_size: int = 10,
        resolve_references: bool = True,
        use_cache: bool = True,
    ) -> JudilibreSearchResponse | None:
        """
        Search decisions in Judilibre.

        Args:
            query: Search keywords.
            jurisdiction: Filter by jurisdiction (cc, ca, tj).
            chamber: Filter by chamber.
            formation: Filter by formation.
            publication: Filter by publication level (b, r, l, c).
            solution: Filter by solution type.
            type_decision: Filter by decision type (arret, qpc, ordonnance).
            theme: Filter by theme/matter.
            date_start: Start date filter (YYYY-MM-DD).
            date_end: End date filter (YYYY-MM-DD).
            operator: Query operator (or, and, exact).
            sort: Sort field (score, date, scorepub).
            order: Sort order (asc, desc).
            page: Page number (0-indexed).
            page_size: Results per page (max 50).
            resolve_references: Whether to resolve taxonomy references.
            use_cache: Whether to use caching.

        Returns:
            JudilibreSearchResponse or None.
        """
        with track_request("judilibre_search", query=query, page=page) as ctx:
            # Build cache key
            cache_key = f"judilibre:search:{query}:{jurisdiction}:{page}:{sort}"

            if use_cache:
                cached = get_cached(cache_key)
                if cached is not None:
                    CacheStats.record_hit()
                    ctx.cache_hit = True
                    try:
                        return JudilibreSearchResponse.model_validate(cached)
                    except ValidationError:
                        pass
                CacheStats.record_miss()

            # Build params
            params: dict[str, Any] = {
                "query": query,
                "page": page,
                "page_size": min(page_size, 50),
                "resolve_references": str(resolve_references).lower(),
                "operator": operator,
                "sort": sort,
                "order": order,
            }

            if jurisdiction:
                params["jurisdiction"] = jurisdiction
            if chamber:
                params["chamber"] = chamber
            if formation:
                params["formation"] = formation
            if publication:
                params["publication"] = publication
            if solution:
                params["solution"] = solution
            if type_decision:
                params["type"] = type_decision
            if theme:
                params["theme"] = theme
            if date_start:
                params["date_start"] = date_start
            if date_end:
                params["date_end"] = date_end

            data = await self._execute_get("/search", params)
            if not data:
                log_api_response("judilibre_search", ctx.duration_ms, True, result_count=0)
                return None

            try:
                response = JudilibreSearchResponse.model_validate(data)

                # Cache the result
                if use_cache and response.results:
                    ttl = get_cache_ttl("search")
                    set_cached(cache_key, data, ttl)

                log_api_response(
                    "judilibre_search", ctx.duration_ms, True,
                    result_count=len(response.results)
                )
                return response

            except ValidationError as ve:
                slog.warning("Judilibre search validation error: %s", str(ve)[:200])
                # Try to return partial data
                return JudilibreSearchResponse(
                    page=data.get("page", 0),
                    page_size=data.get("page_size", 10),
                    total=data.get("total", 0),
                    results=[],
                )

    async def get_decision(
        self,
        decision_id: str,
        query: str | None = None,
        resolve_references: bool = True,
        use_cache: bool = True,
    ) -> JudilibreDecision | None:
        """
        Get a full decision by ID.

        Args:
            decision_id: The decision's unique identifier.
            query: Optional query for highlighting matching terms.
            resolve_references: Whether to resolve taxonomy references.
            use_cache: Whether to use caching.

        Returns:
            JudilibreDecision or None.
        """
        with track_request("judilibre_decision", decision_id=decision_id) as ctx:
            cache_key = f"judilibre:decision:{decision_id}"

            if use_cache:
                cached = get_cached(cache_key)
                if cached is not None:
                    CacheStats.record_hit()
                    ctx.cache_hit = True
                    try:
                        return JudilibreDecision.model_validate(cached)
                    except ValidationError:
                        pass
                CacheStats.record_miss()

            params: dict[str, Any] = {
                "id": decision_id,
                "resolve_references": str(resolve_references).lower(),
            }
            if query:
                params["query"] = query

            try:
                data = await self._execute_get("/decision", params)
                if not data:
                    log_api_response(
                        "judilibre_decision", ctx.duration_ms, True,
                        decision_id=decision_id, found=False
                    )
                    return None

                response = JudilibreDecision.model_validate(data)

                # Cache the result
                if use_cache:
                    ttl = get_cache_ttl("document")
                    set_cached(cache_key, data, ttl)

                log_api_response(
                    "judilibre_decision", ctx.duration_ms, True,
                    decision_id=decision_id, found=True
                )
                return response

            except LegifranceClientError as e:
                if e.status_code == 404:
                    return None
                raise
            except ValidationError as ve:
                slog.warning("Judilibre decision validation error: %s", str(ve)[:200])
                return None

    async def get_taxonomy(
        self,
        taxonomy_id: str | None = None,
        key: str | None = None,
        value: str | None = None,
        context_value: str | None = None,
    ) -> JudilibreTaxonomyResult | None:
        """
        Get taxonomy data for filters.

        Args:
            taxonomy_id: Taxonomy type (type, jurisdiction, chamber, etc.).
            key: Get value for a specific key.
            value: Get key for a specific value.
            context_value: Context for contextual taxonomies (cc, ca).

        Returns:
            JudilibreTaxonomyResult or None.
        """
        params: dict[str, Any] = {}

        if taxonomy_id:
            params["id"] = taxonomy_id
        if key:
            params["key"] = key
        if value:
            params["value"] = value
        if context_value:
            params["context_value"] = context_value

        data = await self._execute_get("/taxonomy", params)
        if not data:
            return None

        try:
            return JudilibreTaxonomyResult.model_validate(data)
        except ValidationError:
            return JudilibreTaxonomyResult(
                id=data.get("id"),
                results=data.get("results") if isinstance(data.get("results"), list) else None,
            )
