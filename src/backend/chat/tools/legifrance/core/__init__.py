"""Core utilities for Legifrance tools.

This module contains shared logic used by the Legifrance tools:
- models: Data classes for documents and search results
- schemas: Pydantic models for API response validation
- criteria: Search criteria builders
- urls: URL generation utilities
- parser: Result parsing utilities
- search: Core search orchestrator
"""

from .criteria import SearchCriterion, SearchField, SearchFilter, build_default_criteria
from .inputs import (
    EtatTexte,
    GetDocumentInput,
    Juridiction,
    ListCodesInput,
    SearchAdminInput,
    SearchCodeArticleInput,
    SearchCodesLoisInput,
    SearchConventionsInput,
    SearchJurisprudenceInput,
    SortOrder,
    TypeSourceAdmin,
    TypeSourceCode,
    TypeSourceConvention,
    validate_input,
)
from .models import LegifranceCodeInfo, LegifranceDocument, LegifranceSearchResult
from .parser import flatten_search_result, format_result_item
from .schemas import (
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
from .search import legifrance_search_core
from .text_utils import clean_text
from .urls import build_source_with_title, get_legifrance_url

__all__ = [
    # Models (dataclasses)
    "LegifranceSearchResult",
    "LegifranceCodeInfo",
    "LegifranceDocument",
    # Schemas (Pydantic)
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
    # Input validation (Pydantic)
    "SearchCodesLoisInput",
    "SearchJurisprudenceInput",
    "SearchConventionsInput",
    "SearchAdminInput",
    "GetDocumentInput",
    "SearchCodeArticleInput",
    "ListCodesInput",
    "TypeSourceCode",
    "TypeSourceConvention",
    "TypeSourceAdmin",
    "Juridiction",
    "SortOrder",
    "EtatTexte",
    "validate_input",
    # Criteria
    "SearchCriterion",
    "SearchField",
    "SearchFilter",
    "build_default_criteria",
    # URLs
    "get_legifrance_url",
    "build_source_with_title",
    # Parser
    "flatten_search_result",
    "format_result_item",
    # Search
    "legifrance_search_core",
    # Text utilities
    "clean_text",
]
