"""Tool for searching in French Jurisprudence."""

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


@last_model_retry_soft_fail
async def legifrance_search_jurisprudence(
    ctx: RunContext[Any],
    query: str,
    date: str | None = None,
    juridiction: str = JURIDICTION_JUDICIAIRE,
    numero_decision: str | None = None,
    sort: str | None = SORT_PERTINENCE,
) -> ToolReturn:
    """
    Recherche dans la jurisprudence via Legifrance - TOUTES JURIDICTIONS.

    ⚠️ QUAND UTILISER CET OUTIL vs judilibre_search :
    - Utilisez LEGIFRANCE pour : Conseil d'État (ADMINISTRATIF), Conseil constitutionnel (QPC),
      Cour des comptes (FINANCIER), ou recherche multi-juridictions
    - Utilisez JUDILIBRE pour : Cour de cassation, Cours d'appel, Tribunaux judiciaires
      (Judilibre offre des données plus riches pour le droit privé/travail)

    Cet outil couvre la jurisprudence administrative, constitutionnelle et financière
    qui n'est PAS disponible dans Judilibre.

    Args:
        ctx: The run context.
        query: Mots-clés de recherche.
        date: Date de la décision (YYYY-MM-DD).
        juridiction: Type de juridiction (JUDICIAIRE, ADMINISTRATIF, CONSTITUTIONNEL, FINANCIER).
        numero_decision: Numéro de la décision.
        sort: Ordre de tri (PERTINENCE, DATE_DESC, DATE_ASC).

    Returns:
        ToolReturn with formatted results and metadata.
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
            raise ModelCannotRetry(str(e)) from e

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
            filtres.append(SearchFilter(facette=FACET_NUMERO_DECISION, valeurs=[numero_decision]))

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
            ctx=ctx,
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

                date_dec = r.raw.get("date") or r.raw.get("dateDecision")
                if date_dec:
                    meta.append(f"Date: {date_dec}")

                output.append(format_result_item(r, fond, meta))

                if r.id:
                    # Pass juridiction as context and raw_data for fallback extraction
                    source = build_source_with_title(
                        r.id, fond, r.title, r.num, r.etat, context=juridiction, raw_data=r.raw
                    )
                    if source:
                        url, title = source
                        # For jurisprudence, no deduplication needed (each decision is unique)
                        sources[url] = title

        if not output:
            return ToolReturn(
                return_value="Aucun résultat trouvé.",
                metadata={
                    "query": query,
                    "fond": fond,
                    "juridiction": juridiction,
                    "sources": {},
                },
            )

        return ToolReturn(
            return_value="\n".join(output),
            metadata={
                "query": query,
                "fond": fond,
                "juridiction": juridiction,
                "sources": sources,
            },
        )

    except (ModelCannotRetry, ModelRetry):
        raise
    except Exception as exc:
        logger.exception("Unexpected error in legifrance_search_jurisprudence: %s", exc)
        raise ModelCannotRetry(
            f"Erreur inattendue: {type(exc).__name__}. "
            "Vous devez expliquer ce problème à l'utilisateur."
        ) from exc
