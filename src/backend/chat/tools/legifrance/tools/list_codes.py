"""Tool for listing available French legal codes."""

from __future__ import annotations

import logging
from typing import Any

from pydantic_ai import RunContext
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.messages import ToolReturn

from chat.tools.exceptions import ModelCannotRetry
from chat.tools.utils import last_model_retry_soft_fail

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


@last_model_retry_soft_fail
async def legifrance_list_codes(ctx: RunContext[Any], code_name: str = "") -> ToolReturn:
    """
    Liste les codes juridiques disponibles sur Légifrance.

    ⚠️ UTILISE CET OUTIL pour vérifier le nom exact d'un code AVANT de chercher.
    Beaucoup de recherches échouent à cause d'un nom de code inexistant
    (ex: "Code constitutionnel" N'EXISTE PAS).

    Args:
        ctx: The run context.
        code_name: Filtre par nom (ex: "urbanisme" pour trouver "Code de l'urbanisme").
                   Laisse vide pour lister tous les codes.

    Returns:
        ToolReturn with formatted list of codes and metadata.
    """
    try:
        # Validate input parameters
        try:
            validated = validate_input(ListCodesInput, code_name=code_name)
            code_name = validated.code_name
        except ValueError as e:
            raise ModelCannotRetry(str(e)) from e

        client = LegifranceAPI()
        results = await client.list_codes(code_name=code_name)

        if not results:
            return ToolReturn(
                return_value="Aucun code trouvé.",
                metadata={
                    "code_name_filter": code_name,
                    "found": False,
                    "count": 0,
                    "sources": set(),
                },
            )

        output = []
        sources = set()

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

            output.append(f"- {code.title} (CID: {code.cid or code.id}) [{code.etat}]{url_snippet}")

            if url:
                sources.add(url)

        return ToolReturn(
            return_value="\n".join(output),
            metadata={
                "code_name_filter": code_name,
                "found": True,
                "count": len(results),
                "sources": sources,
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
        logger.exception("Unexpected error in legifrance_list_codes: %s", exc)
        raise ModelCannotRetry(
            f"Erreur inattendue: {type(exc).__name__}. "
            "Vous devez expliquer ce problème à l'utilisateur."
        ) from exc
