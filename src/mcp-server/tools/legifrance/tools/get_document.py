"""Tool for retrieving full legal documents from Legifrance.

Standalone version (no pydantic-ai dependency).
"""

from __future__ import annotations

import logging
from typing import Any

from ..api import LegifranceAPI
from ..exceptions import (
    LegifranceAPIError,
    LegifranceDocumentNotFoundError,
    LegifranceParseError,
    LegifranceRateLimitError,
    LegifranceServerError,
    LegifranceTimeoutError,
)
from ..core import GetDocumentInput, LegifranceDocument, get_legifrance_url, validate_input

logger = logging.getLogger(__name__)


async def legifrance_get_document(article_id: str) -> dict:
    """
    Get the full text of a legal document from Legifrance.

    Use this to read the content of any document found via search
    (Article, Law, Decision, Agreement, etc.).

    Args:
        article_id: The unique identifier (e.g. "LEGIARTI...", "JORFTEXT...",
                   "KALITEXT...", "JURITEXT...").

    Returns:
        Dict with document content and metadata.
    """
    try:
        # Validate input parameters
        try:
            validated = validate_input(GetDocumentInput, article_id=article_id)
            article_id = validated.article_id
        except ValueError as e:
            return {"error": str(e), "results": "", "sources": {}}

        client = LegifranceAPI()
        data = await client.get_document(article_id)

        if data is None:
            return {
                "results": f"Document non trouve: {article_id}",
                "found": False,
                "sources": {},
            }

        doc = LegifranceDocument.from_raw(
            data, article_id, url_builder=get_legifrance_url
        )

        formatted_output = (
            f"Titre: {doc.title}\n"
            f"Date: {doc.date}\n"
            f"ID: {doc.id}\n"
            f"Lien: {doc.url}\n\n"
            f"{doc.text}"
        )

        return {
            "results": formatted_output,
            "title": doc.title,
            "date": doc.date,
            "url": doc.url,
            "found": True,
            "sources": {doc.url: doc.title} if doc.url else {},
        }

    except LegifranceDocumentNotFoundError:
        return {
            "results": f"Document non trouve: {article_id}",
            "found": False,
            "sources": {},
        }

    except LegifranceParseError as e:
        logger.error("Error parsing document %s: %s", article_id, e)
        return {
            "results": f"Erreur lors du traitement du document {article_id}: format invalide",
            "found": False,
            "error": "parse_error",
            "sources": {},
        }

    except Exception as exc:
        logger.exception("Unexpected error in legifrance_get_document: %s", exc)
        return {
            "error": f"Erreur inattendue: {type(exc).__name__}: {exc}",
            "results": "",
            "sources": {},
        }
