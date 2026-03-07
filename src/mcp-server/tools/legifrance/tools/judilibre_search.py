"""Tool for searching in Judilibre (French Court of Cassation open data).

Standalone version (no pydantic-ai dependency).
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from ..judilibre_api import JudilibreAPI

logger = logging.getLogger(__name__)

# Judilibre constants
JUDILIBRE_BASE_URL = "https://www.courdecassation.fr/decision"

# Jurisdiction codes
JURISDICTION_CC = "cc"  # Cour de cassation
JURISDICTION_CA = "ca"  # Cours d'appel
JURISDICTION_TJ = "tj"  # Tribunaux judiciaires

# Solution types
SOLUTION_CASSATION = "cassation"
SOLUTION_REJET = "rejet"
SOLUTION_ANNULATION = "annulation"
SOLUTION_IRRECEVABILITE = "irrecevabilite"

# Publication levels
PUBLICATION_BULLETIN = "b"
PUBLICATION_RAPPORT = "r"
PUBLICATION_LETTRE = "l"


class JudilibreSearchInput(BaseModel):
    """Validated input for Judilibre search."""

    query: str = Field(..., min_length=2, description="Search keywords")
    jurisdiction: str | None = Field(
        default=JURISDICTION_CC,
        description="Jurisdiction: cc (Cour de cassation), ca (Cours d'appel), tj (Tribunaux)",
    )
    date_start: str | None = Field(
        default=None,
        description="Start date (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    date_end: str | None = Field(
        default=None,
        description="End date (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    solution: str | None = Field(
        default=None,
        description="Solution type (cassation, rejet, annulation, irrecevabilite)",
    )
    publication: str | None = Field(
        default=None,
        description="Publication level (b=Bulletin, r=Rapport, l=Lettre)",
    )


def _format_decision(result: dict[str, Any]) -> str:
    """Format a single decision for display."""
    parts = []

    # Title with number and date
    decision_id = result.get("id", "")
    number = result.get("number", "N/A")
    date = result.get("decision_date", "")
    jurisdiction = result.get("jurisdiction", "")
    chamber = result.get("chamber", "")

    title = f"**{jurisdiction}** - {chamber}" if chamber else f"**{jurisdiction}**"
    parts.append(f"{title}")
    parts.append(f"N. {number} | Date: {date}")

    # Decision ID and URL (needed for judilibre_get_decision and citation)
    if decision_id:
        parts.append(f"ID: {decision_id}")
        parts.append(f"URL: {JUDILIBRE_BASE_URL}/{decision_id}")

    # ECLI
    ecli = result.get("ecli")
    if ecli:
        parts.append(f"ECLI: {ecli}")

    # Solution and publication
    solution = result.get("solution")
    publication = result.get("publication", [])
    if solution or publication:
        meta = []
        if solution:
            meta.append(f"Solution: {solution}")
        if publication:
            pub_str = ", ".join(publication) if isinstance(publication, list) else publication
            meta.append(f"Publication: {pub_str}")
        parts.append(" | ".join(meta))

    # Summary (truncated)
    summary = result.get("summary", "")
    if summary:
        if len(summary) > 500:
            summary = summary[:500] + "..."
        parts.append(f"\n{summary}")

    # Themes
    themes = result.get("themes", [])
    if themes:
        theme_str = ", ".join(themes[:5])
        if len(themes) > 5:
            theme_str += f" (+{len(themes) - 5} autres)"
        parts.append(f"Themes: {theme_str}")

    return "\n".join(parts)


def _build_decision_url(decision_id: str, number: str | None = None) -> str:
    """Build URL for a Judilibre decision."""
    # Judilibre decisions use the internal ID
    return f"{JUDILIBRE_BASE_URL}/{decision_id}"


async def judilibre_search(
    query: str,
    jurisdiction: str | None = JURISDICTION_CC,
    date_start: str | None = None,
    date_end: str | None = None,
    solution: str | None = None,
    publication: str | None = None,
) -> dict:
    """
    Recherche dans Judilibre - base de donnees open data de la COUR DE CASSATION.

    Args:
        query: Mots-cles de recherche (ex: "licenciement", "responsabilite civile").
        jurisdiction: Juridiction (cc=Cour de cassation, ca=Cours d'appel, tj=Tribunaux).
        date_start: Date de debut (YYYY-MM-DD).
        date_end: Date de fin (YYYY-MM-DD).
        solution: Type de solution (cassation, rejet, annulation, irrecevabilite).
        publication: Niveau de publication (b=Bulletin, r=Rapport, l=Lettre).

    Returns:
        Dict with "results" and "sources".
    """
    try:
        # Validate input
        try:
            validated = JudilibreSearchInput(
                query=query,
                jurisdiction=jurisdiction,
                date_start=date_start,
                date_end=date_end,
                solution=solution,
                publication=publication,
            )
        except Exception as e:
            return {"error": f"Parametres invalides: {e}", "results": "", "sources": {}}

        # Execute search
        api = JudilibreAPI()

        response = await api.search(
            query=validated.query,
            jurisdiction=validated.jurisdiction,
            date_start=validated.date_start,
            date_end=validated.date_end,
            solution=validated.solution,
            publication=validated.publication,
            page_size=10,
            resolve_references=True,
        )

        if not response or not response.results:
            return {
                "results": "Aucune decision trouvee dans Judilibre pour cette recherche.",
                "sources": {},
            }

        # Format results
        output = [
            f"**{response.total} decisions trouvees** (affichage des {len(response.results)} premieres)\n"
        ]
        sources: dict[str, str] = {}

        for result in response.results:
            # Convert Pydantic model to dict
            result_dict = result.model_dump()

            output.append(_format_decision(result_dict))
            output.append("---")

            # Build source
            decision_id = result_dict.get("id")
            if decision_id:
                url = _build_decision_url(decision_id, result_dict.get("number"))
                title = f"{result_dict.get('jurisdiction', 'Judilibre')} - {result_dict.get('number', decision_id)}"
                sources[url] = title

        return {
            "results": "\n".join(output),
            "sources": sources,
        }

    except Exception as exc:
        logger.exception("Error in judilibre_search: %s", exc)
        return {
            "error": f"Erreur lors de la recherche Judilibre: {type(exc).__name__}: {exc}",
            "results": "",
            "sources": {},
        }
