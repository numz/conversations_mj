"""Tool for searching for a specific article number in a legal code.

Standalone version (no pydantic-ai dependency).
"""

from __future__ import annotations

import logging
from typing import Any

from ..api import LegifranceAPI
from ..constants import FOND_CODE_DATE
from ..core import SearchCodeArticleInput, build_source_with_title, validate_input
from ..exceptions import (
    LegifranceAPIError,
    LegifranceRateLimitError,
    LegifranceServerError,
    LegifranceTimeoutError,
)

logger = logging.getLogger(__name__)


async def legifrance_search_code_article_by_number(
    code_name: str, article_num: str
) -> dict:
    """
    Search for a specific article NUMBER in a specific CODE.

    Use this when the user asks for "Article X of Code Y".
    This tool uses a precise search strategy (EXACTE on article number).

    Args:
        code_name: The name of the Code (e.g. "Code penal", "Code civil").
        article_num: The article number (e.g. "1240", "123-1", "63").

    Returns:
        Dict with "results" and "sources".
    """
    try:
        # Validate input parameters
        try:
            validated = validate_input(
                SearchCodeArticleInput,
                code_name=code_name,
                article_num=article_num,
            )
            code_name = validated.code_name
            article_num = validated.article_num
        except ValueError as e:
            return {"error": str(e), "results": "", "sources": {}}

        client = LegifranceAPI()
        results = await client.search_code_article(code_name, article_num)

        if not results:
            return {
                "results": (
                    f"Aucun article trouve pour le numero '{article_num}' "
                    f"dans '{code_name}' via la recherche exacte."
                ),
                "found": False,
                "sources": {},
            }

        logger.info(
            "Found %d exact articles for %s Art. %s",
            len(results),
            code_name,
            article_num,
        )

        output = []
        sources: dict[str, str] = {}  # url -> title

        for r in results:
            cid = r.get("titles", [{}])[0].get("cid", "")
            title = r.get("titles", [{}])[0].get("title", "")

            # Check sections for extracts
            sections = r.get("sections", [])
            code_entry = f"- {cid}: {title}"
            if code_entry not in output:
                output.append(code_entry)

            if sections:
                for s in sections:
                    for ext in s.get("extracts", []):
                        ext_id = ext.get("id")
                        etitle = ext.get("title", "")
                        legal_status = ext.get("legalStatus", "")
                        evalues = ext.get("values", [])
                        value_text = " ".join(evalues) if evalues else ""
                        snippet = (
                            f"\n  - {ext_id}: {etitle} ({legal_status}) "
                            f"texte: {value_text}"
                        )
                        if snippet not in output:
                            output.append(snippet)

                        if ext_id:
                            # Build source with meaningful title and raw_data for fallback
                            source = build_source_with_title(
                                ext_id,
                                FOND_CODE_DATE,
                                etitle,
                                article_num,
                                legal_status,
                                context=code_name,
                                raw_data=r,  # Pass parent result for context extraction
                            )
                            if source:
                                url, display_title = source
                                sources[url] = display_title

            if cid:
                # Build source for the code itself with raw_data for fallback
                source = build_source_with_title(
                    cid, FOND_CODE_DATE, title, context=code_name, raw_data=r
                )
                if source:
                    url, display_title = source
                    sources[url] = display_title

        return {
            "results": "\n".join(output),
            "found": True,
            "sources": sources,
        }

    except Exception as exc:
        logger.exception(
            "Unexpected error in legifrance_search_code_article_by_number: %s", exc
        )
        return {
            "error": f"Erreur inattendue: {type(exc).__name__}: {exc}",
            "results": "",
            "sources": {},
        }
