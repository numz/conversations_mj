"""Legifrance API client and tools package.

Standalone version (no Django, pydantic-ai, or langfuse dependencies).

Structure:
    - api: HTTP client for Legifrance API
    - judilibre_api: HTTP client for Judilibre API
    - core: Shared models, criteria builders, parsers
    - tools: Individual tool functions
    - exceptions: Error hierarchy
    - constants: API constants and configuration
    - cache: In-memory caching with TTL
    - logging_utils: Structured logging and metrics
"""

from .api import LegifranceAPI
from .judilibre_api import JudilibreAPI
from .exceptions import (
    LegifranceAPIError,
    LegifranceAuthError,
    LegifranceClientError,
    LegifranceConnectionError,
    LegifranceDocumentNotFoundError,
    LegifranceError,
    LegifranceParseError,
    LegifranceRateLimitError,
    LegifranceServerError,
    LegifranceTimeoutError,
)

# Tool functions
from .tools import (
    legifrance_get_document,
    legifrance_list_codes,
    legifrance_search_admin,
    legifrance_search_code_article_by_number,
    legifrance_search_codes_lois,
    legifrance_search_conventions,
    legifrance_search_jurisprudence,
    # Judilibre tools
    judilibre_search,
    judilibre_get_decision,
)

# Core utilities (for advanced usage)
from .core import (
    LegifranceCodeInfo,
    LegifranceDocument,
    LegifranceSearchResult,
    SearchCriterion,
    SearchField,
    SearchFilter,
    build_default_criteria,
    clean_text,
    flatten_search_result,
    format_result_item,
    get_legifrance_url,
    legifrance_search_core,
)

# Pydantic schemas (for API response validation)
from .core import (
    AccoResponse,
    ArticleData,
    ArticleResponse,
    CodeListItem,
    CodeListResponse,
    GenericDocumentResponse,
    JurisprudenceResponse,
    OAuthResponse,
    SearchResponse,
    SearchResult,
    validate_code_list_response,
    validate_document_response,
    validate_oauth_response,
    validate_search_response,
)

__all__ = [
    # API Clients
    "LegifranceAPI",
    "JudilibreAPI",
    # Exceptions
    "LegifranceError",
    "LegifranceAPIError",
    "LegifranceAuthError",
    "LegifranceRateLimitError",
    "LegifranceServerError",
    "LegifranceClientError",
    "LegifranceTimeoutError",
    "LegifranceConnectionError",
    "LegifranceDocumentNotFoundError",
    "LegifranceParseError",
    # Legifrance Tools
    "legifrance_search_codes_lois",
    "legifrance_search_jurisprudence",
    "legifrance_search_conventions",
    "legifrance_search_admin",
    "legifrance_get_document",
    "legifrance_search_code_article_by_number",
    "legifrance_list_codes",
    # Judilibre Tools
    "judilibre_search",
    "judilibre_get_decision",
    # Core - Models
    "LegifranceSearchResult",
    "LegifranceCodeInfo",
    "LegifranceDocument",
    # Core - Criteria
    "SearchCriterion",
    "SearchField",
    "SearchFilter",
    "build_default_criteria",
    # Core - Utilities
    "get_legifrance_url",
    "flatten_search_result",
    "format_result_item",
    "legifrance_search_core",
    "clean_text",
    # Pydantic Schemas
    "OAuthResponse",
    "SearchResponse",
    "SearchResult",
    "ArticleResponse",
    "ArticleData",
    "JurisprudenceResponse",
    "AccoResponse",
    "CodeListResponse",
    "CodeListItem",
    "GenericDocumentResponse",
    "validate_oauth_response",
    "validate_search_response",
    "validate_code_list_response",
    "validate_document_response",
]
