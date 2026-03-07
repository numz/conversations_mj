"""Search criteria builders for Legifrance tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from ..constants import (
    DEFAULT_OPERATOR,
    SEARCH_FIELD_ALL,
    SEARCH_TYPE_UN_DES_MOTS,
)


@dataclass
class SearchCriterion:
    """Represents a single search criterion like EXACTE or UN_DES_MOTS."""

    typeRecherche: str
    valeur: str
    operateur: str = "ET"
    proximite: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to API-compatible dictionary."""
        d: dict[str, Any] = {
            "typeRecherche": self.typeRecherche,
            "valeur": self.valeur,
            "operateur": self.operateur,
        }
        if self.proximite is not None:
            d["proximite"] = self.proximite
        return d


@dataclass
class SearchField:
    """Represents a search field containing multiple criteria."""

    typeChamp: str
    criteres: list[SearchCriterion]
    operateur: str = "ET"

    def to_dict(self) -> dict[str, Any]:
        """Convert to API-compatible dictionary."""
        return {
            "typeChamp": self.typeChamp,
            "criteres": [c.to_dict() for c in self.criteres],
            "operateur": self.operateur,
        }


@dataclass
class SearchFilter:
    """Represents an API filter facet or singleDate."""

    facette: str
    valeurs: Optional[list[str]] = None
    singleDate: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to API-compatible dictionary."""
        d: dict[str, Any] = {"facette": self.facette}
        if self.valeurs is not None:
            d["valeurs"] = self.valeurs
        if self.singleDate is not None:
            d["singleDate"] = self.singleDate
        return d


def build_default_criteria(
    query: str,
    search_field: str = SEARCH_FIELD_ALL,
    operator: str = DEFAULT_OPERATOR,
) -> list[SearchField]:
    """
    Build standard search criteria for a query.

    Args:
        query: The search query.
        search_field: The field type to search in.
        operator: The logical operator (ET/OU).

    Returns:
        List of SearchField objects for the API.
    """
    if search_field == SEARCH_FIELD_ALL:
        return [
            SearchField(
                typeChamp=SEARCH_FIELD_ALL,
                criteres=[
                    SearchCriterion(
                        typeRecherche=SEARCH_TYPE_UN_DES_MOTS,
                        valeur=query,
                        operateur=operator,
                        proximite=2,
                    )
                ],
                operateur=operator,
            )
        ]
    else:
        return [
            SearchField(
                typeChamp=search_field,
                criteres=[
                    SearchCriterion(
                        typeRecherche=SEARCH_TYPE_UN_DES_MOTS,
                        valeur=query,
                        operateur=operator,
                    )
                ],
                operateur=operator,
            )
        ]
