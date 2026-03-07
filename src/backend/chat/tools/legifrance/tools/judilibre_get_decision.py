"""Tool for getting a full decision from Judilibre."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import RunContext
from pydantic_ai.messages import ToolReturn

from chat.tools.exceptions import ModelCannotRetry
from chat.tools.utils import last_model_retry_soft_fail

from ..judilibre_api import JudilibreAPI

logger = logging.getLogger(__name__)

JUDILIBRE_BASE_URL = "https://www.courdecassation.fr/decision"


class JudilibreGetDecisionInput(BaseModel):
    """Validated input for getting a Judilibre decision."""

    decision_id: str = Field(..., min_length=10, description="Judilibre decision ID")


def _format_full_decision(decision: dict[str, Any]) -> str:
    """Format a full decision for display."""
    parts = []

    # Header
    jurisdiction = decision.get("jurisdiction", "")
    chamber = decision.get("chamber", "")
    number = decision.get("number", "N/A")
    date = decision.get("decision_date", "")

    parts.append(f"# {jurisdiction} - {chamber}")
    parts.append(f"**Numéro:** {number}")
    parts.append(f"**Date:** {date}")

    # ECLI
    ecli = decision.get("ecli")
    if ecli:
        parts.append(f"**ECLI:** {ecli}")

    # Solution and type
    solution = decision.get("solution")
    decision_type = decision.get("type")
    if solution:
        parts.append(f"**Solution:** {solution}")
    if decision_type:
        parts.append(f"**Type:** {decision_type}")

    # Publication
    publication = decision.get("publication", [])
    if publication:
        pub_str = ", ".join(publication) if isinstance(publication, list) else publication
        parts.append(f"**Publication:** {pub_str}")

    # Summary
    summary = decision.get("summary")
    if summary:
        parts.append(f"\n## Résumé\n{summary}")

    # Themes
    themes = decision.get("themes", [])
    if themes:
        parts.append(f"\n## Thèmes\n- " + "\n- ".join(themes))

    # Visa (legal references)
    visa = decision.get("visa", [])
    if visa:
        parts.append("\n## Visa (textes appliqués)")
        for v in visa:
            title = v.get("title", "")
            if title:
                parts.append(f"- {title}")

    # Rapprochements (related jurisprudence)
    rapprochements = decision.get("rapprochements", [])
    if rapprochements:
        parts.append("\n## Jurisprudence connexe")
        for r in rapprochements[:5]:  # Limit to 5
            title = r.get("title", "")
            if title:
                parts.append(f"- {title}")
        if len(rapprochements) > 5:
            parts.append(f"- (+{len(rapprochements) - 5} autres)")

    # Contested decision
    contested = decision.get("contested")
    if contested and isinstance(contested, dict):
        contested_date = contested.get("date", "")
        contested_title = contested.get("title", "")
        if contested_title or contested_date:
            parts.append(f"\n## Décision attaquée\n{contested_title} ({contested_date})")

    # Full text (truncated if very long)
    text = decision.get("text", "")
    if text:
        parts.append("\n## Texte intégral")
        if len(text) > 8000:
            parts.append(text[:8000] + "\n\n[...texte tronqué pour lisibilité...]")
        else:
            parts.append(text)

    return "\n".join(parts)


@last_model_retry_soft_fail
async def judilibre_get_decision(
    ctx: RunContext[Any],
    decision_id: str,
) -> ToolReturn:
    """
    Récupère le contenu COMPLET d'une décision de la Cour de cassation via Judilibre.

    Utilisez cet outil après judilibre_search pour obtenir :
    - Le texte intégral de la décision
    - Les textes de visa (articles de loi appliqués)
    - Les rapprochements de jurisprudence (décisions similaires)
    - Les thèmes et mots-clés détaillés
    - La décision attaquée (cour d'appel d'origine)

    ⚠️ Cet outil est spécifique aux décisions Judilibre (Cour de cassation, CA, TJ).
    Pour les décisions du Conseil d'État ou Conseil constitutionnel, utilisez
    legifrance_get_document avec l'ID obtenu via legifrance_search_jurisprudence.

    Args:
        ctx: The run context.
        decision_id: L'identifiant unique Judilibre (ex: "6079c56a9ba5988459c57490").

    Returns:
        ToolReturn with the full decision content.
    """
    try:
        # Validate input
        try:
            validated = JudilibreGetDecisionInput(decision_id=decision_id)
        except Exception as e:
            raise ModelCannotRetry(f"Paramètre invalide: {e}") from e

        # Fetch decision
        api = JudilibreAPI()

        decision = await api.get_decision(
            decision_id=validated.decision_id,
            resolve_references=True,
        )

        if not decision:
            return ToolReturn(
                return_value=f"Décision non trouvée: {decision_id}",
                metadata={
                    "decision_id": decision_id,
                    "found": False,
                    "sources": {},
                },
            )

        # Convert to dict and format
        decision_dict = decision.model_dump()
        formatted = _format_full_decision(decision_dict)

        # Build source URL
        url = f"{JUDILIBRE_BASE_URL}/{decision_id}"
        number = decision_dict.get("number", decision_id)
        jurisdiction = decision_dict.get("jurisdiction", "Judilibre")
        title = f"{jurisdiction} - {number}"

        return ToolReturn(
            return_value=formatted,
            metadata={
                "decision_id": decision_id,
                "number": number,
                "jurisdiction": jurisdiction,
                "found": True,
                "sources": {url: title},
            },
        )

    except ModelCannotRetry:
        raise
    except Exception as exc:
        logger.exception("Error in judilibre_get_decision: %s", exc)
        raise ModelCannotRetry(
            f"Erreur lors de la récupération de la décision: {type(exc).__name__}. "
            "Vérifiez l'identifiant et réessayez."
        ) from exc
