"""Tool for retrieving full legal documents from Legifrance."""

from __future__ import annotations

import logging
from typing import Any

from pydantic_ai import RunContext
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.messages import ToolReturn

from chat.tools.exceptions import ModelCannotRetry
from chat.tools.utils import last_model_retry_soft_fail

from ..api import LegifranceAPI
from ..core import GetDocumentInput, LegifranceDocument, get_legifrance_url, validate_input
from ..exceptions import (
    LegifranceAPIError,
    LegifranceDocumentNotFoundError,
    LegifranceParseError,
    LegifranceRateLimitError,
    LegifranceServerError,
    LegifranceTimeoutError,
)

logger = logging.getLogger(__name__)


@last_model_retry_soft_fail
async def legifrance_get_document(ctx: RunContext[Any], article_id: str) -> ToolReturn:
    """
    Get the full text of a legal document from Legifrance.

    Use this to read the content of any document found via search
    (Article, Law, Decision, Agreement, etc.).

    Args:
        ctx: The run context.
        article_id: The unique identifier (e.g. "LEGIARTI...", "JORFTEXT...",
                   "KALITEXT...", "JURITEXT...").

    Returns:
        ToolReturn with document content and metadata.
    """
    try:
        # Validate input parameters
        try:
            validated = validate_input(GetDocumentInput, article_id=article_id)
            article_id = validated.article_id
        except ValueError as e:
            raise ModelCannotRetry(str(e)) from e

        client = LegifranceAPI()
        data = await client.get_document(article_id)

        if data is None:
            return ToolReturn(
                return_value=f"Document non trouvé: {article_id}",
                metadata={
                    "article_id": article_id,
                    "found": False,
                    "sources": {},
                },
            )

        doc = LegifranceDocument.from_raw(data, article_id, url_builder=get_legifrance_url)

        formatted_output = (
            f"Titre: {doc.title}\nDate: {doc.date}\nID: {doc.id}\nLien: {doc.url}\n\n{doc.text}"
        )

        return ToolReturn(
            return_value=formatted_output,
            metadata={
                "article_id": article_id,
                "title": doc.title,
                "date": doc.date,
                "url": doc.url,
                "found": True,
                "sources": {doc.url: doc.title} if doc.url else {},
            },
        )

    except LegifranceDocumentNotFoundError:
        return ToolReturn(
            return_value=f"Document non trouvé: {article_id}",
            metadata={
                "article_id": article_id,
                "found": False,
                "sources": {},
            },
        )

    except LegifranceParseError as e:
        logger.error("Error parsing document %s: %s", article_id, e)
        return ToolReturn(
            return_value=f"Erreur lors du traitement du document {article_id}: format invalide",
            metadata={
                "article_id": article_id,
                "found": False,
                "error": "parse_error",
                "sources": {},
            },
        )

    except LegifranceRateLimitError as e:
        logger.warning("Legifrance rate limited: %s", e)
        raise ModelRetry(
            "L'API Legifrance est temporairement surchargée. Réessai en cours..."
        ) from e

    except (LegifranceTimeoutError, LegifranceServerError) as e:
        logger.warning("Legifrance transient error: %s", e)
        raise ModelRetry(
            "Le serveur Legifrance rencontre des difficultés. Réessai en cours..."
        ) from e

    except LegifranceAPIError as e:
        logger.error("Legifrance API error: %s", e)
        raise ModelCannotRetry(
            f"Erreur Legifrance: {e}. Vous devez expliquer ce problème à l'utilisateur."
        ) from e

    except (ModelCannotRetry, ModelRetry):
        raise

    except Exception as exc:
        logger.exception("Unexpected error in legifrance_get_document: %s", exc)
        raise ModelCannotRetry(
            f"Erreur inattendue: {type(exc).__name__}. "
            "Vous devez expliquer ce problème à l'utilisateur."
        ) from exc
