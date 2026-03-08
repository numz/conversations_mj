"""Tool for searching for a specific article number in a legal code."""

from __future__ import annotations

import logging
from typing import Any

from pydantic_ai import RunContext
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.messages import ToolReturn

from chat.tools.exceptions import ModelCannotRetry
from chat.tools.utils import last_model_retry_soft_fail

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


@last_model_retry_soft_fail
async def legifrance_search_code_article_by_number(
    ctx: RunContext[Any], code_name: str, article_num: str
) -> ToolReturn:
    """
    Recherche un article par son NUMÉRO EXACT dans un Code. C'est l'outil LE PLUS FIABLE.

    ✅ UTILISE CET OUTIL EN PRIORITÉ quand tu connais le numéro d'article.
    Exemples : article 1242 du Code civil, article L. 121-1 du Code pénal,
    article 49-3 de la Constitution.

    Args:
        ctx: The run context.
        code_name: Nom exact du Code (ex: "Code pénal", "Code civil",
                   "Code de procédure pénale"). Utilise legifrance_list_codes
                   si tu n'es pas sûr du nom.
        article_num: Numéro de l'article (ex: "1240", "L. 121-1", "49-3").

    Returns:
        ToolReturn with formatted results and metadata.
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
            raise ModelCannotRetry(str(e)) from e

        client = LegifranceAPI()
        results = await client.search_code_article(code_name, article_num)

        if not results:
            return ToolReturn(
                return_value=(
                    f"Aucun article trouvé pour le numéro '{article_num}' "
                    f"dans '{code_name}' via la recherche exacte."
                ),
                metadata={
                    "code_name": code_name,
                    "article_num": article_num,
                    "found": False,
                    "sources": {},
                },
            )

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
                        snippet = f"\n  - {ext_id}: {etitle} ({legal_status}) texte: {value_text}"
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

        return ToolReturn(
            return_value="\n".join(output),
            metadata={
                "code_name": code_name,
                "article_num": article_num,
                "found": True,
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
        logger.exception("Unexpected error in legifrance_search_code_article_by_number: %s", exc)
        raise ModelCannotRetry(
            f"Erreur inattendue: {type(exc).__name__}. "
            "Vous devez expliquer ce problème à l'utilisateur."
        ) from exc
