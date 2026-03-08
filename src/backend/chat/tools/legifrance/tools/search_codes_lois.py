"""Tool for searching in French Codes and Laws."""

from __future__ import annotations

import datetime
import logging
import re
from typing import Any, Optional

from pydantic_ai import RunContext
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.messages import ToolReturn

from chat.tools.exceptions import ModelCannotRetry
from chat.tools.utils import last_model_retry_soft_fail

from ..constants import (
    DEFAULT_OPERATOR,
    FACET_ARTICLE_LEGAL_STATUS,
    FACET_DATE_VERSION,
    FACET_NOM_CODE,
    FOND_CODE_DATE,
    FOND_CODE_ETAT,
    FOND_LODA_DATE,
    FOND_PREFIX_CODE,
    FOND_PREFIX_LODA,
    LEGAL_STATUS_VIGUEUR,
    SEARCH_FIELD_ALL,
    SEARCH_TYPE_EXACTE,
    SORT_PERTINENCE,
    SORT_PUBLICATION_DATE_DESC,
    TYPE_SOURCE_CODE,
    TYPE_SOURCE_CODE_DATE,
    TYPE_SOURCE_LODA,
)
from ..core import (
    SearchCodeArticleInput,
    SearchCodesLoisInput,
    SearchCriterion,
    SearchField,
    SearchFilter,
    build_default_criteria,
    build_source_with_title,
    flatten_search_result,
    format_result_item,
    legifrance_search_core,
    validate_input,
)
from ..core.code_name_validator import validate_code_name

logger = logging.getLogger(__name__)


@last_model_retry_soft_fail
async def legifrance_search_codes_lois(
    ctx: RunContext[Any],
    query: str,
    type_source: str = TYPE_SOURCE_CODE,
    code_name: str = "Code pénal",
    date: str | None = None,
) -> ToolReturn:
    """
    Recherche par mots-clés dans les Codes et les Lois/Décrets.

    ⚠️ Si tu connais le numéro exact d'un article, utilise plutôt
    legifrance_search_code_article_by_number qui est plus fiable.

    IMPORTANT pour la requête :
    - Utilise des mots-clés COURTS (2-4 mots). Ex: "garde chose", "préfet", "1240".
    - NE PAS écrire de phrases longues (elles échouent systématiquement).
    - NE PAS mettre de guillemets dans la requête.
    - Le "Code constitutionnel" N'EXISTE PAS. Pour la Constitution, utilise
      type_source="LODA" avec query="Constitution" ou search_admin(source="JORF").

    Args:
        ctx: The run context.
        query: Mots-clés courts (2-4 mots max). Ex: "1240", "garde chose", "préfet".
        type_source: "CODE" (Codes en vigueur) ou "LODA" (Lois et Décrets). Défaut: "CODE".
        code_name: Nom EXACT du code (ex: "Code civil", "Code pénal"). Utilise
                   legifrance_list_codes si tu n'es pas sûr du nom.
        date: Date de vigueur (YYYY-MM-DD). Défaut = Aujourd'hui.

    Returns:
        ToolReturn with formatted results and metadata.
    """
    try:
        # Validate input parameters
        try:
            validated = validate_input(
                SearchCodesLoisInput,
                query=query,
                type_source=type_source,
                code_name=code_name,
                date=date,
            )
            query = validated.query
            type_source = validated.type_source.value
            code_name = validated.code_name
            date = validated.date
        except ValueError as e:
            raise ModelCannotRetry(str(e)) from e

        # Validate code_name against real Legifrance code list (CODE only)
        if code_name and type_source in (TYPE_SOURCE_CODE, TYPE_SOURCE_CODE_DATE):
            try:
                code_name = await validate_code_name(code_name)
            except ValueError as e:
                raise ModelCannotRetry(str(e)) from e

        # Heuristic: Check if query is typically an article lookup
        match = re.match(r"^\s*(?:article|art\.?)\s+([LRDA]?\s*[\d\.-]+)\s*$", query, re.IGNORECASE)
        if not match:
            if re.match(r"^[LRDA]?\s*[\d\.-]+\s*$", query, re.IGNORECASE):
                match = re.search(r"([LRDA]?\s*[\d\.-]+)", query)

        clean_num = None
        actual_type_source = type_source
        actual_query = query

        if match:
            clean_num = match.group(1).strip()
            if code_name and type_source == TYPE_SOURCE_CODE:
                actual_query = clean_num
                # Force CODE_DATE for exact article search in code
                actual_type_source = TYPE_SOURCE_CODE_DATE

        # Determine Fond
        fond = FOND_CODE_DATE  # Default for CODE
        if actual_type_source == TYPE_SOURCE_LODA:
            fond = FOND_LODA_DATE
        elif actual_type_source == TYPE_SOURCE_CODE_DATE:
            fond = FOND_CODE_DATE

        # Criteria
        criteres = []
        if fond == FOND_CODE_DATE and clean_num:
            # Exact search strategy for Article Number
            criteres.append(
                SearchField(
                    typeChamp=SEARCH_FIELD_ALL,
                    criteres=[
                        SearchCriterion(
                            typeRecherche=SEARCH_TYPE_EXACTE,
                            valeur=actual_query,
                            operateur=DEFAULT_OPERATOR,
                        )
                    ],
                    operateur=DEFAULT_OPERATOR,
                )
            )
        else:
            criteres = build_default_criteria(actual_query)

        # Filters
        filtres = []
        if code_name and fond.startswith(FOND_PREFIX_CODE):
            filtres.append(SearchFilter(facette=FACET_NOM_CODE, valeurs=[code_name]))

        # LODA State filter
        if fond.startswith(FOND_PREFIX_LODA):
            if not date:
                filtres.append(
                    SearchFilter(facette=FACET_ARTICLE_LEGAL_STATUS, valeurs=[LEGAL_STATUS_VIGUEUR])
                )

        # Date Filter
        if date:
            try:
                dt = datetime.datetime.strptime(date, "%Y-%m-%d")
                ts = int(dt.timestamp() * 1000)
                filtres.append(SearchFilter(facette=FACET_DATE_VERSION, singleDate=ts))
            except ValueError:
                logger.warning("Invalid date format: %s", date)
        elif fond == FOND_CODE_ETAT:
            filtres.append(
                SearchFilter(facette=FACET_ARTICLE_LEGAL_STATUS, valeurs=[LEGAL_STATUS_VIGUEUR])
            )

        # Sort
        sort = SORT_PERTINENCE
        if fond.startswith(FOND_PREFIX_LODA):
            sort = SORT_PUBLICATION_DATE_DESC

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
                if r.date_publication:
                    dp = r.date_publication
                    if not dp.startswith("2999"):
                        meta.append(f"Publi: {dp.split('T')[0]}")

                output.append(format_result_item(r, fond, meta))

                if r.id:
                    # Pass code_name as context and raw_data for fallback extraction
                    source = build_source_with_title(
                        r.id, fond, r.title, r.num, r.etat, context=code_name, raw_data=r.raw
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
                                # Replace abrogated version with current version
                                seen_articles[r.num] = (url, title, is_vigueur)
                        else:
                            # No article number, add directly
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
                    "code_name": code_name,
                    "sources": {},
                },
            )

        return ToolReturn(
            return_value="\n".join(output),
            metadata={
                "query": query,
                "fond": fond,
                "code_name": code_name,
                "sources": sources,
            },
        )

    except (ModelCannotRetry, ModelRetry):
        raise
    except Exception as exc:
        logger.exception("Unexpected error in legifrance_search_codes_lois: %s", exc)
        raise ModelCannotRetry(
            f"Erreur inattendue: {type(exc).__name__}. "
            "Vous devez expliquer ce problème à l'utilisateur."
        ) from exc
