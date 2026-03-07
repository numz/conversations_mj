"""Tool for listing available French legal codes.

Standalone version (no pydantic-ai dependency).
"""

from __future__ import annotations

import logging
from typing import Any

from ..api import LegifranceAPI
from ..constants import ID_PREFIX_LEGITEXT, LEGIFRANCE_UI_BASE_URL, UI_PATH_CODES_TEXTE
from ..core import LegifranceCodeInfo, ListCodesInput, validate_input
from ..exceptions import (
    LegifranceAPIError,
    LegifranceRateLimitError,
    LegifranceServerError,
    LegifranceTimeoutError,
)

logger = logging.getLogger(__name__)


async def legifrance_list_codes(code_name: str = "") -> dict:
    """
    List available legal codes in France.

    Use this to find the EXACT name of a code if queries where code was needed
    returns nothing.

    Args:
        code_name: Filter by code name (e.g. "urbanisme" to find "Code de l'urbanisme").
                   Leave empty to list all codes.

    Returns:
        Dict with "results" and "sources".
    """
    try:
        # Validate input parameters
        try:
            validated = validate_input(ListCodesInput, code_name=code_name)
            code_name = validated.code_name
        except ValueError as e:
            return {"error": str(e), "results": "", "sources": {}}

        client = LegifranceAPI()
        results = await client.list_codes(code_name=code_name)

        if not results:
            return {
                "results": "Aucun code trouve.",
                "found": False,
                "count": 0,
                "sources": {},
            }

        output = []
        sources: dict[str, str] = {}

        for r in results:
            code = LegifranceCodeInfo(
                id=r.get("id", "?"),
                title=r.get("title") or r.get("titre") or "Sans titre",
                etat=r.get("etat", ""),
                cid=r.get("cid"),
            )

            url = ""
            if code.cid and code.cid.startswith(ID_PREFIX_LEGITEXT):
                url = f"{LEGIFRANCE_UI_BASE_URL}/{UI_PATH_CODES_TEXTE}/{code.cid}"

            url_snippet = f"\n  Lien: {url}" if url else ""

            output.append(
                f"- {code.title} (CID: {code.cid or code.id}) [{code.etat}]{url_snippet}"
            )

            if url:
                sources[url] = code.title

        return {
            "results": "\n".join(output),
            "found": True,
            "count": len(results),
            "sources": sources,
        }

    except Exception as exc:
        logger.exception("Unexpected error in legifrance_list_codes: %s", exc)
        return {
            "error": f"Erreur inattendue: {type(exc).__name__}: {exc}",
            "results": "",
            "sources": {},
        }
