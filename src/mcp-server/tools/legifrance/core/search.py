"""Core search orchestrator for Legifrance tools.

Standalone version (no pydantic-ai dependency).
"""

from __future__ import annotations

import logging
from typing import Any

from ..constants import DEFAULT_OPERATOR, SORT_PERTINENCE
from ..exceptions import (
    LegifranceAuthError,
    LegifranceClientError,
    LegifranceConnectionError,
    LegifranceRateLimitError,
    LegifranceServerError,
    LegifranceTimeoutError,
)
from .criteria import SearchField, SearchFilter

logger = logging.getLogger(__name__)


async def legifrance_search_core(
    query: str,
    fond: str,
    criteres: list[SearchField],
    filtres: list[SearchFilter],
    sort: str = SORT_PERTINENCE,
) -> list[dict[str, Any]]:
    """
    Core search orchestrator for Legifrance.

    Executes a search and converts API exceptions to regular exceptions
    or returns empty lists for non-retryable errors.

    Args:
        query: The search query.
        fond: The document source (fond).
        criteres: List of search criteria.
        filtres: List of search filters.
        sort: Sort order for results.

    Returns:
        List of raw search results.

    Raises:
        LegifranceRateLimitError: For rate limit errors.
        LegifranceTimeoutError: For timeout errors.
        LegifranceConnectionError: For connection errors.
        LegifranceServerError: For server errors.
        LegifranceAuthError: For authentication errors.
        LegifranceClientError: For client errors.
    """
    # Late import to avoid circular dependency (api.py imports core.schemas)
    from ..api import LegifranceAPI

    client = LegifranceAPI()

    try:
        results = await client.search(
            criteres=[c.to_dict() for c in criteres],
            filtres=[f.to_dict() for f in filtres],
            fond=fond,
            sort=sort,
            operateur=DEFAULT_OPERATOR,
        )

        if not results:
            logger.debug("No results found for query: %s in fond: %s", query, fond)
            return []

        logger.debug("Found %d results for query: %s", len(results), query)
        return results

    except LegifranceRateLimitError as e:
        logger.warning("Legifrance rate limited: %s", e)
        raise

    except LegifranceTimeoutError as e:
        logger.warning("Legifrance timeout: %s", e)
        raise

    except LegifranceConnectionError as e:
        logger.warning("Legifrance connection error: %s", e)
        raise

    except LegifranceServerError as e:
        logger.warning("Legifrance server error: %s", e)
        raise

    except LegifranceAuthError as e:
        logger.error("Legifrance auth error: %s", e)
        raise

    except LegifranceClientError as e:
        logger.error("Legifrance client error: %s", e)
        raise

    except Exception as e:
        logger.exception("Unexpected error in Legifrance search: %s", e)
        raise
