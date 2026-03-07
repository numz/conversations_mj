"""Pydantic models for validating tool input parameters.

These models provide input validation with clear error messages
for the Legifrance tools.
"""

from __future__ import annotations

import re
from datetime import date
from enum import Enum
from typing import Annotated, Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# TypeVar for validate_input return type
T = TypeVar("T", bound=BaseModel)


# =============================================================================
# Enums for constrained string values
# =============================================================================


class TypeSourceCode(str, Enum):
    """Valid type_source values for code/law search."""

    CODE = "CODE"
    CODE_DATE = "CODE_DATE"
    LODA = "LODA"


class TypeSourceConvention(str, Enum):
    """Valid type_source values for convention search."""

    KALI = "KALI"
    ACCO = "ACCO"


class TypeSourceAdmin(str, Enum):
    """Valid source values for admin search."""

    JORF = "JORF"
    CIRC = "CIRC"
    CNIL = "CNIL"


class Juridiction(str, Enum):
    """Valid juridiction values."""

    JUDICIAIRE = "JUDICIAIRE"
    ADMINISTRATIF = "ADMINISTRATIF"
    CONSTITUTIONNEL = "CONSTITUTIONNEL"
    FINANCIER = "FINANCIER"


class SortOrder(str, Enum):
    """Valid sort order values."""

    PERTINENCE = "PERTINENCE"
    DATE_DESC = "DATE_DESC"
    DATE_ASC = "DATE_ASC"


class EtatTexte(str, Enum):
    """Valid etat_texte values."""

    VIGUEUR = "VIGUEUR"
    ABROGE = "ABROGE"
    MODIFIE = "MODIFIE"


# =============================================================================
# Custom validators
# =============================================================================

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ARTICLE_ID_PATTERN = re.compile(
    r"^(LEGIARTI|LEGITEXT|JURITEXT|CETATEXT|CONSTEXT|JUFITEXT|"
    r"CNILTEXT|ACCOTEXT|JORFTEXT|JORFARTI|KALITEXT|KALIARTI|CEHR)\d+$"
)


def validate_date_format(v: str | None) -> str | None:
    """Validate date string is in YYYY-MM-DD format."""
    if v is None:
        return None
    if not DATE_PATTERN.match(v):
        raise ValueError(
            f"Date invalide '{v}'. Format attendu: YYYY-MM-DD (ex: 2024-01-15)"
        )
    # Also validate it's a real date
    try:
        year, month, day = map(int, v.split("-"))
        date(year, month, day)
    except ValueError as e:
        raise ValueError(f"Date invalide '{v}': {e}") from e
    return v


def validate_non_empty_query(v: str) -> str:
    """Validate query string is not empty or whitespace-only."""
    if not v or not v.strip():
        raise ValueError("La requête ne peut pas être vide")
    return v.strip()


def validate_article_id(v: str) -> str:
    """Validate article ID format."""
    if not v or not v.strip():
        raise ValueError("L'identifiant du document ne peut pas être vide")
    v = v.strip().upper()
    # Allow purely numeric IDs (for circulaires)
    if v.isdigit():
        return v
    # Check if it looks like a Legifrance ID (letters followed by digits)
    # If so, it must match the known prefix pattern
    if re.match(r"^[A-Z]+\d+$", v):
        if not ARTICLE_ID_PATTERN.match(v):
            raise ValueError(
                f"Format d'identifiant invalide '{v}'. "
                "Formats acceptés: LEGIARTI..., LEGITEXT..., JURITEXT..., etc."
            )
    return v


# =============================================================================
# Input models for each tool
# =============================================================================


class SearchCodesLoisInput(BaseModel):
    """Input validation for legifrance_search_codes_lois."""

    model_config = ConfigDict(str_strip_whitespace=True)

    query: Annotated[str, Field(min_length=1, description="Mots-clés ou numéro d'article")]
    type_source: TypeSourceCode = TypeSourceCode.CODE
    code_name: str = "Code pénal"
    date: str | None = None

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        return validate_non_empty_query(v)

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str | None) -> str | None:
        return validate_date_format(v)


class SearchJurisprudenceInput(BaseModel):
    """Input validation for legifrance_search_jurisprudence."""

    model_config = ConfigDict(str_strip_whitespace=True)

    query: Annotated[str, Field(min_length=1, description="Mots-clés de recherche")]
    date: str | None = None
    juridiction: Juridiction = Juridiction.JUDICIAIRE
    numero_decision: str | None = None
    sort: SortOrder | None = SortOrder.PERTINENCE

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        return validate_non_empty_query(v)

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str | None) -> str | None:
        return validate_date_format(v)


class SearchConventionsInput(BaseModel):
    """Input validation for legifrance_search_conventions."""

    model_config = ConfigDict(str_strip_whitespace=True)

    query: Annotated[str, Field(min_length=1, description="Mots-clés de recherche")]
    type_source: TypeSourceConvention = TypeSourceConvention.KALI
    idcc: str | None = None
    date: str | None = None
    etat_texte: EtatTexte | None = EtatTexte.VIGUEUR

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        return validate_non_empty_query(v)

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str | None) -> str | None:
        return validate_date_format(v)

    @field_validator("idcc")
    @classmethod
    def validate_idcc(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if v and not v.isdigit():
            raise ValueError(
                f"IDCC invalide '{v}'. L'IDCC doit être un nombre (ex: 1090)"
            )
        return v


class SearchAdminInput(BaseModel):
    """Input validation for legifrance_search_admin."""

    model_config = ConfigDict(str_strip_whitespace=True)

    query: Annotated[str, Field(min_length=1, description="Mots-clés de recherche")]
    source: TypeSourceAdmin = TypeSourceAdmin.JORF
    date: str | None = None
    nor: str | None = None
    nature_delib: str | None = None

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        return validate_non_empty_query(v)

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str | None) -> str | None:
        return validate_date_format(v)

    @field_validator("nor")
    @classmethod
    def validate_nor(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip().upper()
        # NOR format: XXXAXXXXXXX (3 letters + A + 7 alphanum)
        if v and len(v) != 12:
            raise ValueError(
                f"Format NOR invalide '{v}'. "
                "Le NOR doit contenir 12 caractères (ex: ECOX2300001A)"
            )
        return v


class GetDocumentInput(BaseModel):
    """Input validation for legifrance_get_document."""

    model_config = ConfigDict(str_strip_whitespace=True)

    article_id: Annotated[
        str,
        Field(min_length=1, description="Identifiant du document")
    ]

    @field_validator("article_id")
    @classmethod
    def validate_article_id(cls, v: str) -> str:
        return validate_article_id(v)


class SearchCodeArticleInput(BaseModel):
    """Input validation for legifrance_search_code_article_by_number."""

    model_config = ConfigDict(str_strip_whitespace=True)

    code_name: Annotated[
        str,
        Field(min_length=1, description="Nom du code (ex: Code pénal)")
    ]
    article_num: Annotated[
        str,
        Field(min_length=1, description="Numéro d'article (ex: 1240, L123-1)")
    ]

    @field_validator("code_name")
    @classmethod
    def validate_code_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Le nom du code ne peut pas être vide")
        return v.strip()

    @field_validator("article_num")
    @classmethod
    def validate_article_num(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Le numéro d'article ne peut pas être vide")
        return v.strip()


class ListCodesInput(BaseModel):
    """Input validation for legifrance_list_codes."""

    model_config = ConfigDict(str_strip_whitespace=True)

    code_name: str = ""

    @field_validator("code_name")
    @classmethod
    def clean_code_name(cls, v: str) -> str:
        return v.strip() if v else ""


# =============================================================================
# Validation helper function
# =============================================================================


def validate_input(model_class: type[T], **kwargs: Any) -> T:
    """
    Validate input parameters using a Pydantic model.

    Args:
        model_class: The Pydantic model class to use for validation.
        **kwargs: The input parameters to validate.

    Returns:
        The validated model instance.

    Raises:
        ValueError: If validation fails, with a user-friendly message.
    """
    try:
        return model_class(**kwargs)
    except Exception as e:
        # Extract validation error messages
        error_messages = []
        if hasattr(e, "errors"):
            for error in e.errors():
                field = ".".join(str(loc) for loc in error.get("loc", []))
                msg = error.get("msg", str(error))
                if field:
                    error_messages.append(f"{field}: {msg}")
                else:
                    error_messages.append(msg)
        else:
            error_messages.append(str(e))

        raise ValueError(
            "Paramètres invalides:\n- " + "\n- ".join(error_messages)
        ) from e
