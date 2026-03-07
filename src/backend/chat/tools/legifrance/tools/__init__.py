"""Legifrance individual tools package.

This module exports all Legifrance tool functions and re-exports
core utilities for convenience.
"""

# Tool functions
# Re-export core utilities for convenience
from ..core import (
    LegifranceCodeInfo,
    LegifranceDocument,
    LegifranceSearchResult,
    SearchCriterion,
    SearchField,
    SearchFilter,
    build_default_criteria,
    flatten_search_result,
    format_result_item,
    get_legifrance_url,
    legifrance_search_core,
)
from .get_document import legifrance_get_document
from .judilibre_get_decision import judilibre_get_decision

# Judilibre tools (Cour de cassation open data)
from .judilibre_search import judilibre_search
from .list_codes import legifrance_list_codes
from .search_admin import legifrance_search_admin
from .search_code_article_by_number import legifrance_search_code_article_by_number
from .search_codes_lois import legifrance_search_codes_lois
from .search_conventions import legifrance_search_conventions
from .search_jurisprudence import legifrance_search_jurisprudence

__all__ = [
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
    # Models (from core)
    "LegifranceSearchResult",
    "LegifranceCodeInfo",
    "LegifranceDocument",
    # Search criteria (from core)
    "SearchCriterion",
    "SearchField",
    "SearchFilter",
    "build_default_criteria",
    # Utilities (from core)
    "get_legifrance_url",
    "flatten_search_result",
    "format_result_item",
    "legifrance_search_core",
]
