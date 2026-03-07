"""Legifrance API client and tools package.

Structure:
    - api: HTTP client for Legifrance API
    - core: Shared models, criteria builders, parsers
    - tools: Individual tool functions for the agent
    - exceptions: Error hierarchy
    - constants: API constants and configuration
"""

from .api import LegifranceAPI

# Core utilities (for advanced usage)
# Pydantic schemas (for API response validation)
from .core import (
    AccoResponse,
    ArticleData,
    ArticleResponse,
    CodeListItem,
    CodeListResponse,
    GenericDocumentResponse,
    JurisprudenceResponse,
    LegifranceCodeInfo,
    LegifranceDocument,
    LegifranceSearchResult,
    OAuthResponse,
    SearchCriterion,
    SearchField,
    SearchFilter,
    SearchResponse,
    SearchResult,
    build_default_criteria,
    clean_text,
    flatten_search_result,
    format_result_item,
    get_legifrance_url,
    legifrance_search_core,
    validate_code_list_response,
    validate_document_response,
    validate_oauth_response,
    validate_search_response,
)
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
from .judilibre_api import JudilibreAPI

# Tool functions
from .tools import (
    judilibre_get_decision,
    # Judilibre tools
    judilibre_search,
    legifrance_get_document,
    legifrance_list_codes,
    legifrance_search_admin,
    legifrance_search_code_article_by_number,
    legifrance_search_codes_lois,
    legifrance_search_conventions,
    legifrance_search_jurisprudence,
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
