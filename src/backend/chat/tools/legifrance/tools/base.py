"""
Shared helpers for Legifrance tools.

This module re-exports components from the core module for backwards compatibility.
New code should import directly from legifrance.core.
"""

# Re-export everything from core
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

# Aliases for backwards compatibility (private function names)
_build_default_criteria = build_default_criteria
_get_legifrance_url = get_legifrance_url
_flatten_search_result = flatten_search_result
_format_result_item = format_result_item
_legifrance_search_core = legifrance_search_core

__all__ = [
    # Models
    "LegifranceSearchResult",
    "LegifranceCodeInfo",
    "LegifranceDocument",
    # Search criteria
    "SearchCriterion",
    "SearchField",
    "SearchFilter",
    "build_default_criteria",
    # URL utilities
    "get_legifrance_url",
    # Result parser
    "flatten_search_result",
    "format_result_item",
    # Search core
    "legifrance_search_core",
    # Backwards compatibility aliases
    "_build_default_criteria",
    "_get_legifrance_url",
    "_flatten_search_result",
    "_format_result_item",
    "_legifrance_search_core",
]
