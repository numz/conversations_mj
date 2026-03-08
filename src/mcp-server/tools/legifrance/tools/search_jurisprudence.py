"""Tool for searching in French Jurisprudence.

Standalone version (no pydantic-ai dependency).
"""

from __future__ import annotations

import datetime
import logging
from typing import Any

from ..constants import (
    FACET_DATE_DECISION,
    FACET_NUMERO_DECISION,
    FOND_CETAT,
    FOND_CONSTIT,
    FOND_JUFI,
    FOND_JURI,
    JURIDICTION_ADMINISTRATIF,
    JURIDICTION_CONSTITUTIONNEL,
    JURIDICTION_FINANCIER,
    JURIDICTION_JUDICIAIRE,
    SORT_DATE_ASC,
    SORT_DATE_DESC,
    SORT_PERTINENCE,
)
from ..core import (
    SearchFilter,
    SearchJurisprudenceInput,
    build_default_criteria,
    build_source_with_title,
    flatten_search_result,
    format_result_item,
    legifrance_search_core,
    validate_input,
)

logger = logging.getLogger(__name__)


async def legifrance_search_jurisprudence(
    query: str,
    date: str | None = None,
    juridiction: str = JURIDICTION_JUDICIAIRE,
    numero_decision: str | None = None,
    sort: str | None = SORT_PERTINENCE,
) -> dict:
    """
    Recherche dans la jurisprudence via Legifrance - TOUTES JURIDICTIONS.

    Args:
        query: Mots-cles de recherche.
        date: Date de la decision (YYYY-MM-DD).
        juridiction: Type de juridiction (JUDICIAIRE, ADMINISTRATIF, CONSTITUTIONNEL, FINANCIER).
        numero_decision: Numero de la decision.
        sort: Ordre de tri (PERTINENCE, DATE_DESC, DATE_ASC).

    Returns:
        Dict with "results" and "sources".
    """
    try:
        # Validate input parameters
        try:
            validated = validate_input(
                SearchJurisprudenceInput,
                query=query,
                date=date,
                juridiction=juridiction,
                numero_decision=numero_decision,
                sort=sort,
            )
            query = validated.query
            date = validated.date
            juridiction = validated.juridiction.value
            numero_decision = validated.numero_decision
            sort = validated.sort.value if validated.sort else SORT_PERTINENCE
        except ValueError as e:
            return {"error": str(e), "results": "", "sources": {}}

        # Map high-level jurisdiction to technical source
        source_map = {
            JURIDICTION_JUDICIAIRE: FOND_JURI,
            JURIDICTION_ADMINISTRATIF: FOND_CETAT,
            JURIDICTION_CONSTITUTIONNEL: FOND_CONSTIT,
            JURIDICTION_FINANCIER: FOND_JUFI,
        }
        fond = source_map.get(juridiction.upper(), FOND_JURI)

        # Criteria construction
        criteres = build_default_criteria(query)

        # Filters
        filtres = []

        if numero_decision:
            filtres.append(
                SearchFilter(facette=FACET_NUMERO_DECISION, valeurs=[numero_decision])
            )

        if date:
            try:
                dt = datetime.datetime.strptime(date, "%Y-%m-%d")
                ts = int(dt.timestamp() * 1000)
                filtres.append(SearchFilter(facette=FACET_DATE_DECISION, singleDate=ts))
            except ValueError:
                logger.warning("Invalid date format: %s", date)

        # Sort mapping
        api_sort = sort or SORT_PERTINENCE
        if api_sort in [SORT_DATE_DESC, SORT_DATE_ASC]:
            suffix = "_DESC" if "DESC" in api_sort else "_ASC"
            api_sort = f"DATE_DECISION{suffix}"

        raw_results = await legifrance_search_core(
            query=query,
            fond=fond,
            criteres=criteres,
            filtres=filtres,
            sort=api_sort,
        )

        # Build output
        output = []
        sources: dict[str, str] = {}  # url -> title

        for raw_item in raw_results:
            flat_items = flatten_search_result(raw_item)

            for r in flat_items:
                meta = []
                if r.juridiction:
                    meta.append(f"Jur: {r.juridiction}")

                # Extract decision date — may be a string or a timestamp (ms)
                date_dec = (
                    r.raw.get("dateDecision")
                    or r.raw.get("date")
                    or r.raw.get("dateTexte")
                )
                # Also check inside titles (common in search results)
                if not date_dec and r.raw.get("titles"):
                    titles = r.raw["titles"]
                    if isinstance(titles, list) and titles:
                        date_dec = titles[0].get("dateDecision") or titles[0].get("date")
                # Fallback: relevantDate (always a timestamp)
                if not date_dec:
                    date_dec = r.raw.get("relevantDate")

                # Convert timestamp (ms) to readable date
                if date_dec and isinstance(date_dec, (int, float)):
                    try:
                        dt = datetime.datetime.fromtimestamp(date_dec / 1000)
                        date_dec = dt.strftime("%Y-%m-%d")
                    except (ValueError, TypeError, OSError):
                        date_dec = None

                if date_dec:
                    meta.append(f"Date: {date_dec}")

                output.append(format_result_item(r, fond, meta))

                if r.id:
                    # Pass juridiction as context and raw_data for fallback extraction
                    source = build_source_with_title(
                        r.id, fond, r.title, r.num, r.etat,
                        context=juridiction, raw_data=r.raw
                    )
                    if source:
                        url, title = source
                        # For jurisprudence, no deduplication needed (each decision is unique)
                        sources[url] = title

        if not output:
            return {
                "results": "Aucun resultat trouve.",
                "sources": {},
            }

        return {
            "results": "\n".join(output),
            "sources": sources,
        }

    except Exception as exc:
        logger.exception("Unexpected error in legifrance_search_jurisprudence: %s", exc)
        return {
            "error": f"Erreur inattendue: {type(exc).__name__}: {exc}",
            "results": "",
            "sources": {},
        }
