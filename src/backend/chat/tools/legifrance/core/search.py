"""Core search orchestrator for Legifrance tools."""

from __future__ import annotations

import logging
from typing import Any

from pydantic_ai import RunContext
from pydantic_ai.exceptions import ModelRetry

from chat.tools.exceptions import ModelCannotRetry

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
    ctx: RunContext[Any],
    query: str,
    fond: str,
    criteres: list[SearchField],
    filtres: list[SearchFilter],
    sort: str = SORT_PERTINENCE,
) -> list[dict[str, Any]]:
    """
    Core search orchestrator for Legifrance.

    Executes a search and converts API exceptions to ModelRetry/ModelCannotRetry
    for proper handling by the agent framework.

    Args:
        ctx: The run context.
        query: The search query.
        fond: The document source (fond).
        criteres: List of search criteria.
        filtres: List of search filters.
        sort: Sort order for results.

    Returns:
        List of raw search results.

    Raises:
        ModelRetry: For retryable errors (rate limit, timeout, server errors).
        ModelCannotRetry: For non-retryable errors (auth, client errors).
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
        raise ModelRetry(
            "L'API Legifrance est temporairement surchargée. Réessai en cours..."
        ) from e

    except LegifranceTimeoutError as e:
        logger.warning("Legifrance timeout: %s", e)
        raise ModelRetry("La requête Legifrance a expiré. Réessai en cours...") from e

    except LegifranceConnectionError as e:
        logger.warning("Legifrance connection error: %s", e)
        raise ModelRetry("Erreur de connexion à Legifrance. Réessai en cours...") from e

    except LegifranceServerError as e:
        logger.warning("Legifrance server error: %s", e)
        raise ModelRetry(
            "Le serveur Legifrance rencontre des difficultés. Réessai en cours..."
        ) from e

    except LegifranceAuthError as e:
        logger.error("Legifrance auth error: %s", e)
        raise ModelCannotRetry(
            "Erreur d'authentification Legifrance. "
            "Vous devez expliquer ce problème à l'utilisateur."
        ) from e

    except LegifranceClientError as e:
        logger.error("Legifrance client error: %s", e)
        raise ModelCannotRetry(
            f"Erreur de requête Legifrance ({e.status_code}). "
            "Vous devez expliquer ce problème à l'utilisateur."
        ) from e

    except Exception as e:
        logger.exception("Unexpected error in Legifrance search: %s", e)
        raise ModelCannotRetry(
            f"Erreur inattendue Legifrance: {type(e).__name__}. "
            "Vous devez expliquer ce problème à l'utilisateur."
        ) from e
