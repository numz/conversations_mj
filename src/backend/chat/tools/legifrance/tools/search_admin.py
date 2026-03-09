"""Tool for searching JORF, CIRC and CNIL."""

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
    FACET_DATE_DELIB,
    FACET_DATE_VERSION,
    FACET_NATURE_DELIB,
    FACET_NOR,
    FOND_CIRC,
    FOND_CNIL,
    FOND_JORF,
    SEARCH_FIELD_TITLE,
    SORT_DATE_DECISION_DESC,
    SORT_PERTINENCE,
    SORT_PUBLICATION_DATE_DESC,
    SORT_SIGNATURE_DATE_DESC,
    TYPE_SOURCE_JORF,
)
from ..core import (
    SearchAdminInput,
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
async def legifrance_search_admin(
    ctx: RunContext[Any],
    query: str,
    source: str = TYPE_SOURCE_JORF,
    date: str | None = None,
    nor: str | None = None,
    nature_delib: str | None = None,
) -> ToolReturn:
    """
    Recherche dans le Journal Officiel (JORF), Circulaires (CIRC) et CNIL.

    Utilise cet outil pour les textes administratifs, décrets, ordonnances,
    arrêtés, circulaires et délibérations CNIL.

    💡 Pour les textes constitutionnels (Constitution de 1958, révisions),
    cherche dans JORF avec des mots-clés comme "Constitution", "révision constitutionnelle".

    Args:
        ctx: The run context.
        query: Mots-clés courts (2-4 mots). Ex: "dissolution assemblée", "décret préfet".
        source: JORF (Journal Officiel), CIRC (Circulaires) ou CNIL.
        date: Date de publication/délibération (YYYY-MM-DD). Optionnel.
        nor: Numéro NOR du document (si connu).
        nature_delib: Nature de la délibération (pour CNIL uniquement).

    Returns:
        ToolReturn with formatted results and metadata.
    """
    try:
        # Validate input parameters
        try:
            validated = validate_input(
                SearchAdminInput,
                query=query,
                source=source,
                date=date,
                nor=nor,
                nature_delib=nature_delib,
            )
            query = validated.query
            source = validated.source.value
            date = validated.date
            nor = validated.nor
            nature_delib = validated.nature_delib
        except ValueError as e:
            raise ModelCannotRetry(str(e)) from e

        # Clean query if source name is in it
        actual_query = query
        if source in query:
            actual_query = query.replace(source, "").strip()

        fond = source  # JORF, CIRC, CNIL

        # Criteria: use TITLE field for JORF/CIRC to reduce noise
        search_field = SEARCH_FIELD_TITLE if fond in (FOND_JORF, FOND_CIRC) else None
        criteres = build_default_criteria(actual_query, search_field=search_field) if search_field else build_default_criteria(actual_query)

        # Filters
        filtres = []

        # Auto-detect nature from query for JORF to reduce noise
        if fond == FOND_JORF:
            _NATURE_KEYWORDS = {
                "décret": "DECRET",
                "decret": "DECRET",
                "arrêté": "ARRETE",
                "arrete": "ARRETE",
                "ordonnance": "ORDONNANCE",
                "loi": "LOI",
                "circulaire": "CIRCULAIRE",
            }
            query_lower = actual_query.lower()
            for keyword, nature_value in _NATURE_KEYWORDS.items():
                if keyword in query_lower:
                    filtres.append(SearchFilter(facette="NATURE", valeurs=[nature_value]))
                    # Remove the keyword from query to avoid redundancy in title search
                    actual_query = actual_query.replace(keyword, "").replace(keyword.capitalize(), "").replace(keyword.upper(), "").strip()
                    # Rebuild criteria with cleaned query
                    criteres = build_default_criteria(actual_query, search_field=search_field) if search_field else build_default_criteria(actual_query)
                    logger.info("Auto-detected JORF nature filter: %s (cleaned query: '%s')", nature_value, actual_query)
                    break  # Only one nature filter

        if fond == FOND_CNIL:
            if nature_delib:
                filtres.append(SearchFilter(facette=FACET_NATURE_DELIB, valeurs=[nature_delib]))
            if nor:
                filtres.append(SearchFilter(facette=FACET_NOR, valeurs=[nor]))
            if date:
                try:
                    dt_del = datetime.datetime.strptime(date, "%Y-%m-%d")
                    ts_del = int(dt_del.timestamp() * 1000)
                    filtres.append(SearchFilter(facette=FACET_DATE_DELIB, singleDate=ts_del))
                except ValueError:
                    logger.warning("Invalid date format: %s", date)

        if fond in [FOND_JORF, FOND_CIRC] and date:
            try:
                dt = datetime.datetime.strptime(date, "%Y-%m-%d")
                ts = int(dt.timestamp() * 1000)
                filtres.append(SearchFilter(facette=FACET_DATE_VERSION, singleDate=ts))
            except ValueError:
                logger.warning("Invalid date format: %s", date)

        # Sort
        sort = SORT_PERTINENCE
        if fond == FOND_JORF:
            sort = SORT_PUBLICATION_DATE_DESC
        elif fond == FOND_CIRC:
            sort = SORT_SIGNATURE_DATE_DESC
        elif fond == FOND_CNIL:
            sort = SORT_DATE_DECISION_DESC

        raw_results = await legifrance_search_core(
            ctx=ctx,
            query=actual_query,
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
                if fond == FOND_JORF:
                    if r.nature:
                        meta.append(f"Nature: {r.nature}")
                    if r.date_publication:
                        dp = r.date_publication.split("T")[0]
                        meta.append(f"Publi: {dp}")
                elif fond == FOND_CNIL:
                    if r.nature:
                        meta.append(f"Nature: {r.nature}")

                output.append(format_result_item(r, fond, meta))

                if r.id:
                    # Pass fond type as context and raw_data for fallback extraction
                    context = fond  # JORF, CIRC, or CNIL
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
                    "sources": {},
                },
            )

        return ToolReturn(
            return_value="\n".join(output),
            metadata={
                "query": query,
                "fond": fond,
                "sources": sources,
            },
        )

    except (ModelCannotRetry, ModelRetry):
        raise
    except Exception as exc:
        logger.exception("Unexpected error in legifrance_search_admin: %s", exc)
        raise ModelCannotRetry(
            f"Erreur inattendue: {type(exc).__name__}. "
            "Vous devez expliquer ce problème à l'utilisateur."
        ) from exc
