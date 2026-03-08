"""Tool for searching in French Jurisprudence.

Standalone version (no pydantic-ai dependency).
"""

from __future__ import annotations

import datetime
import logging
import re
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

# French month names to numeric mapping
_FRENCH_MONTHS = {
    "janvier": "01", "février": "02", "mars": "03", "avril": "04",
    "mai": "05", "juin": "06", "juillet": "07", "août": "08",
    "septembre": "09", "octobre": "10", "novembre": "11", "décembre": "12",
}

# Pattern: "19 novembre 2013" or "1er janvier 2020"
_DATE_RE = re.compile(
    r"(\d{1,2})(?:er)?\s+("
    + "|".join(_FRENCH_MONTHS.keys())
    + r")\s+(\d{4})",
    re.IGNORECASE,
)


def _extract_french_date(text: str) -> str | None:
    """Extract a date from a French text string like '19 novembre 2013'."""
    m = _DATE_RE.search(text)
    if m:
        day = m.group(1).zfill(2)
        month = _FRENCH_MONTHS.get(m.group(2).lower())
        year = m.group(3)
        if month:
            return f"{year}-{month}-{day}"
    return None


def _normalize_juridiction(value: str) -> str:
    """Normalize juridiction values that LLMs may send with typos or partial names."""
    v = value.strip().upper()
    # Direct match
    valid = {JURIDICTION_JUDICIAIRE, JURIDICTION_ADMINISTRATIF,
             JURIDICTION_CONSTITUTIONNEL, JURIDICTION_FINANCIER}
    if v in valid:
        return v
    # Fuzzy: match by prefix/substring
    for candidate in valid:
        if candidate.startswith(v) or v.startswith(candidate[:5]):
            return candidate
    # Common LLM mistakes
    if "JUDIC" in v or "CASS" in v or "APPEL" in v:
        return JURIDICTION_JUDICIAIRE
    if "ADMIN" in v or "CONSEIL" in v:
        return JURIDICTION_ADMINISTRATIF
    if "CONSTIT" in v:
        return JURIDICTION_CONSTITUTIONNEL
    if "FINANC" in v or "COMPT" in v:
        return JURIDICTION_FINANCIER
    # Default
    return JURIDICTION_JUDICIAIRE


async def legifrance_search_jurisprudence(
    query: str,
    date: str | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
    juridiction: str = JURIDICTION_JUDICIAIRE,
    numero_decision: str | None = None,
    sort: str | None = SORT_PERTINENCE,
) -> dict:
    """
    Recherche dans la jurisprudence via Legifrance - TOUTES JURIDICTIONS.

    Args:
        query: Mots-cles de recherche.
        date: Date exacte de la decision (YYYY-MM-DD).
        date_start: Date de debut de la plage (YYYY-MM-DD).
        date_end: Date de fin de la plage (YYYY-MM-DD).
        juridiction: Type de juridiction (JUDICIAIRE, ADMINISTRATIF, CONSTITUTIONNEL, FINANCIER).
        numero_decision: Numero de la decision.
        sort: Ordre de tri (PERTINENCE, DATE_DESC, DATE_ASC).

    Returns:
        Dict with "results" and "sources".
    """
    try:
        # Sanitize "null" strings sent by LLMs
        if date and str(date).strip().lower() in ("null", "none", ""):
            date = None
        if date_start and str(date_start).strip().lower() in ("null", "none", ""):
            date_start = None
        if date_end and str(date_end).strip().lower() in ("null", "none", ""):
            date_end = None

        # If date_start/date_end are provided alongside date, prefer the range
        if (date_start or date_end) and date:
            date = None

        # Normalize juridiction — LLMs may send partial/wrong values
        juridiction = _normalize_juridiction(juridiction)

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
        elif date_start or date_end:
            ts_start = None
            ts_end = None
            if date_start:
                try:
                    ts_start = int(datetime.datetime.strptime(date_start, "%Y-%m-%d").timestamp() * 1000)
                except ValueError:
                    logger.warning("Invalid date_start format: %s", date_start)
            if date_end:
                try:
                    ts_end = int(datetime.datetime.strptime(date_end, "%Y-%m-%d").timestamp() * 1000)
                except ValueError:
                    logger.warning("Invalid date_end format: %s", date_end)
            # API requires both start and end — default missing bounds
            if ts_start is None and ts_end is not None:
                # Default start to 1800-01-01
                ts_start = int(datetime.datetime(1800, 1, 1).timestamp() * 1000)
            if ts_end is None and ts_start is not None:
                # Default end to today
                ts_end = int(datetime.datetime.now().timestamp() * 1000)
            if ts_start is not None and ts_end is not None:
                filtres.append(SearchFilter(
                    facette=FACET_DATE_DECISION,
                    dateStart=ts_start,
                    dateEnd=ts_end,
                ))

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

                # Last resort: parse French date from title string
                # e.g. "Cour de cassation, ..., 19 novembre 2013, ..."
                if not date_dec and r.title:
                    date_dec = _extract_french_date(r.title)

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
