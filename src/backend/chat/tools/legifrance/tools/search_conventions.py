"""Tool for searching in French Collective Bargaining Agreements and Company Agreements."""

from __future__ import annotations

import datetime
import logging
from typing import Any

from pydantic_ai import RunContext
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.messages import ToolReturn

from chat.tools.exceptions import ModelCannotRetry
from chat.tools.utils import last_model_retry_soft_fail

from ..constants import (
    FACET_DATE_SIGNATURE,
    FACET_IDCC,
    FACET_LEGAL_STATUS,
    FOND_ACCO,
    FOND_KALI,
    LEGAL_STATUS_VIGUEUR,
    SORT_PERTINENCE,
    SORT_SIGNATURE_DATE_DESC,
    TYPE_SOURCE_KALI,
)
from ..core import (
    SearchConventionsInput,
    SearchFilter,
    build_default_criteria,
    build_source_with_title,
    flatten_search_result,
    format_result_item,
    legifrance_search_core,
    validate_input,
)

logger = logging.getLogger(__name__)


@last_model_retry_soft_fail
async def legifrance_search_conventions(
    ctx: RunContext[Any],
    query: str,
    type_source: str = TYPE_SOURCE_KALI,
    idcc: str | None = None,
    date: str | None = None,
    etat_texte: str | None = LEGAL_STATUS_VIGUEUR,
) -> ToolReturn:
    """
    Recherche dans les conventions collectives (KALI) et accords d'entreprise (ACCO).

    Args:
        ctx: The run context.
        query: Mots-clés de recherche.
        type_source: "KALI" (conventions collectives) ou "ACCO" (accords d'entreprise).
        idcc: Identifiant de la convention collective.
        date: Date de signature (YYYY-MM-DD).
        etat_texte: État du texte (VIGUEUR par défaut).

    Returns:
        ToolReturn with formatted results and metadata.
    """
    try:
        # Validate input parameters
        try:
            validated = validate_input(
                SearchConventionsInput,
                query=query,
                type_source=type_source,
                idcc=idcc,
                date=date,
                etat_texte=etat_texte,
            )
            query = validated.query
            type_source = validated.type_source.value
            idcc = validated.idcc
            date = validated.date
            etat_texte = validated.etat_texte.value if validated.etat_texte else None
        except ValueError as e:
            raise ModelCannotRetry(str(e)) from e

        fond = type_source  # KALI or ACCO

        # Criteria
        criteres = build_default_criteria(query)

        # Filters
        filtres = []

        if fond == FOND_ACCO:
            if date:
                try:
                    dt_sig = datetime.datetime.strptime(date, "%Y-%m-%d")
                    ts_sig = int(dt_sig.timestamp() * 1000)
                    filtres.append(SearchFilter(facette=FACET_DATE_SIGNATURE, singleDate=ts_sig))
                except ValueError:
                    logger.warning("Invalid date format: %s", date)
            if idcc:
                filtres.append(SearchFilter(facette=FACET_IDCC, valeurs=[idcc]))

        elif fond == FOND_KALI:
            if etat_texte:
                filtres.append(SearchFilter(facette=FACET_LEGAL_STATUS, valeurs=[etat_texte]))
            if idcc:
                filtres.append(SearchFilter(facette=FACET_IDCC, valeurs=[idcc]))
            if date:
                try:
                    dt_sig = datetime.datetime.strptime(date, "%Y-%m-%d")
                    ts_sig = int(dt_sig.timestamp() * 1000)
                    filtres.append(SearchFilter(facette=FACET_DATE_SIGNATURE, singleDate=ts_sig))
                except ValueError:
                    logger.warning("Invalid date format: %s", date)

        # Sort
        sort = SORT_PERTINENCE
        if fond == FOND_KALI:
            sort = SORT_SIGNATURE_DATE_DESC

        raw_results = await legifrance_search_core(
            ctx=ctx,
            query=query,
            fond=fond,
            criteres=criteres,
            filtres=filtres,
            sort=sort,
        )

        # Build output
        output = []
        sources: dict[str, str] = {}  # url -> title
        seen_articles: dict[str, tuple[str, str, bool]] = {}  # num -> (url, title, is_vigueur)

        for raw_item in raw_results:
            flat_items = flatten_search_result(raw_item)

            for r in flat_items:
                meta = []
                if r.date_signature:
                    ds = r.date_signature.split("T")[0]
                    meta.append(f"Sign: {ds}")

                output.append(format_result_item(r, fond, meta))

                if r.id:
                    # Pass IDCC as context and raw_data for fallback extraction
                    context = f"IDCC {idcc}" if idcc else None
                    source = build_source_with_title(
                        r.id, fond, r.title, r.num, r.etat, context=context, raw_data=r.raw
                    )
                    if source:
                        url, title = source
                        is_vigueur = r.etat and r.etat.upper() in (
                            "VIGUEUR",
                            "EN_VIGUEUR",
                            "EN VIGUEUR",
                        )

                        # Deduplicate by article number, prefer "en vigueur" version
                        if r.num:
                            existing = seen_articles.get(r.num)
                            if existing is None:
                                seen_articles[r.num] = (url, title, is_vigueur)
                            elif is_vigueur and not existing[2]:
                                seen_articles[r.num] = (url, title, is_vigueur)
                        else:
                            sources[url] = title

        # Add deduplicated articles to sources
        for url, title, _ in seen_articles.values():
            sources[url] = title

        if not output:
            return ToolReturn(
                return_value="Aucun résultat trouvé.",
                metadata={
                    "query": query,
                    "fond": fond,
                    "idcc": idcc,
                    "sources": {},
                },
            )

        return ToolReturn(
            return_value="\n".join(output),
            metadata={
                "query": query,
                "fond": fond,
                "idcc": idcc,
                "sources": sources,
            },
        )

    except (ModelCannotRetry, ModelRetry):
        raise
    except Exception as exc:
        logger.exception("Unexpected error in legifrance_search_conventions: %s", exc)
        raise ModelCannotRetry(
            f"Erreur inattendue: {type(exc).__name__}. "
            "Vous devez expliquer ce problème à l'utilisateur."
        ) from exc
