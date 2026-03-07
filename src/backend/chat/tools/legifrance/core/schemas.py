"""Pydantic schemas for Legifrance API response validation.

These models validate API responses and provide type safety
for data flowing through the Legifrance tools.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, cast

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# OAuth Response
# =============================================================================


class OAuthResponse(BaseModel):
    """OAuth token response from Legifrance authentication endpoint."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    scope: Optional[str] = None


# =============================================================================
# Search Response Models
# =============================================================================


class SearchResultExtract(BaseModel):
    """An extract/article within a search result section."""

    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = None
    num: Optional[str] = None
    title: Optional[str] = None
    legalStatus: Optional[str] = Field(default=None, alias="legalStatus")
    etat: Optional[str] = None
    values: list[str] = Field(default_factory=list)


class SearchResultSection(BaseModel):
    """A section within a search result containing extracts."""

    title: Optional[str] = None
    extracts: list[SearchResultExtract] = Field(default_factory=list)


class SearchResultTitle(BaseModel):
    """Title/Code information in a search result."""

    id: Optional[str] = None
    title: Optional[str] = None
    titre: Optional[str] = None  # Alternative field name
    cid: Optional[str] = None

    @property
    def display_title(self) -> str:
        """Get the display title, preferring 'title' over 'titre'."""
        return self.title or self.titre or ""


class SearchResult(BaseModel):
    """A single search result from the Legifrance search endpoint."""

    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None  # id can be in titles[0].id instead
    titles: list[SearchResultTitle] = Field(default_factory=list)
    sections: list[SearchResultSection] = Field(default_factory=list)
    etat: Optional[str] = None
    nature: Optional[str] = None
    date: Optional[str] = None
    juridiction: Optional[str] = None
    # Raw data for any additional fields
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True)


class SearchResponse(BaseModel):
    """Response from the Legifrance search endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    results: list[SearchResult] = Field(default_factory=list)
    totalResultNumber: Optional[int] = Field(default=None, alias="totalResultNumber")
    executionId: Optional[str] = Field(default=None, alias="executionId")


# =============================================================================
# Article/Document Response Models
# =============================================================================


class ArticleVersion(BaseModel):
    """Version information for an article."""

    id: Optional[str] = None
    dateDebut: Optional[int] = None
    dateFin: Optional[int] = None
    etat: Optional[str] = None


class TextTitle(BaseModel):
    """Title information from text context."""

    id: Optional[str] = None
    titre: Optional[str] = None
    cid: Optional[str] = None


class ArticleData(BaseModel):
    """Article content from the consult/getArticle endpoint."""

    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    num: Optional[str] = None
    title: Optional[str] = None
    titre: Optional[str] = None
    text: Optional[str] = None
    texte: Optional[str] = None
    content: Optional[str] = None
    etat: Optional[str] = None
    dateDebut: Optional[int] = None
    dateFin: Optional[int] = None
    dateTexte: Optional[str] = None
    sectionParentTitre: Optional[str] = None
    textTitles: list[TextTitle] = Field(default_factory=list)
    articleVersions: list[ArticleVersion] = Field(default_factory=list)

    @property
    def display_title(self) -> str:
        """Get the display title."""
        return self.title or self.titre or ""

    @property
    def display_text(self) -> str:
        """Get the text content."""
        return self.text or self.texte or self.content or ""


class ArticleResponse(BaseModel):
    """Response wrapper for article consultation."""

    article: Optional[ArticleData] = None
    result: Optional[ArticleData] = None

    def get_article(self) -> Optional[ArticleData]:
        """Get the article data from either wrapper."""
        return self.article or self.result


# =============================================================================
# Jurisprudence Response Models
# =============================================================================


class JurisprudenceText(BaseModel):
    """Jurisprudence document content."""

    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    titre: Optional[str] = None
    text: Optional[str] = None
    texte: Optional[str] = None
    juridiction: Optional[str] = None
    juridictionJudiciaire: Optional[str] = None
    chambre: Optional[str] = None
    dateDecision: Optional[str] = None
    numeroAffaire: Optional[str] = None
    numAffaire: Optional[str] = None

    @property
    def display_juridiction(self) -> str:
        """Get the juridiction."""
        return self.juridiction or self.juridictionJudiciaire or ""


class JurisprudenceResponse(BaseModel):
    """Response wrapper for jurisprudence consultation."""

    model_config = ConfigDict(extra="allow")

    text: Optional[JurisprudenceText] = None


# =============================================================================
# ACCO (Accords d'entreprise) Response Models
# =============================================================================


class AccoAttachment(BaseModel):
    """Attachment content for ACCO documents."""

    content: Optional[str] = None
    filename: Optional[str] = None
    mimeType: Optional[str] = None


class AccoData(BaseModel):
    """ACCO document content."""

    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    titre: Optional[str] = None
    attachment: Optional[AccoAttachment] = None
    dateSignature: Optional[str] = None
    datePublication: Optional[str] = None


class AccoResponse(BaseModel):
    """Response wrapper for ACCO consultation."""

    model_config = ConfigDict(extra="allow")

    acco: Optional[AccoData] = None


# =============================================================================
# Code List Response Models
# =============================================================================


class CodeListItem(BaseModel):
    """A code in the list codes response."""

    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    title: Optional[str] = None
    titre: Optional[str] = None
    cid: Optional[str] = None
    etat: Optional[str] = None
    date: Optional[str] = None

    @property
    def display_title(self) -> str:
        """Get the display title."""
        return self.title or self.titre or ""


class CodeListResponse(BaseModel):
    """Response from the list codes endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    results: list[CodeListItem] = Field(default_factory=list)
    totalResultNumber: Optional[int] = Field(default=None, alias="totalResultNumber")


# =============================================================================
# JORF Response Models
# =============================================================================


class JorfListItem(BaseModel):
    """An item in the JORF list response."""

    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    titre: Optional[str] = None
    nature: Optional[str] = None


class JorfResponse(BaseModel):
    """Response wrapper for JORF consultation."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: Optional[str] = None
    titre: Optional[str] = None
    items: list[JorfListItem] = Field(default_factory=list, alias="list")


# =============================================================================
# Structured Text Response (Codes, Lois with sections)
# =============================================================================


class SectionData(BaseModel):
    """A section in a structured text."""

    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    title: Optional[str] = None
    titre: Optional[str] = None

    @property
    def display_title(self) -> str:
        """Get the display title."""
        return self.title or self.titre or ""


class StructuredArticle(BaseModel):
    """An article in a structured text."""

    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    num: Optional[str] = None
    content: Optional[str] = None
    text: Optional[str] = None


class StructuredTextResponse(BaseModel):
    """Response for structured texts like Codes or Lois."""

    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    titre: Optional[str] = None
    nature: Optional[str] = None
    sections: list[SectionData] = Field(default_factory=list)
    articles: list[StructuredArticle] = Field(default_factory=list)


# =============================================================================
# Generic Document Response (Union type for all document types)
# =============================================================================


class GenericDocumentResponse(BaseModel):
    """
    Generic document response that can handle any document type.

    Use the specific response models when the document type is known,
    or this model when the type is uncertain.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    # Possible wrappers
    article: Optional[dict[str, Any]] = None
    text: Optional[dict[str, Any]] = None
    acco: Optional[dict[str, Any]] = None
    result: Optional[dict[str, Any]] = None

    # Direct fields (for structured texts)
    id: Optional[str] = None
    titre: Optional[str] = None
    nature: Optional[str] = None
    sections: Optional[list[dict[str, Any]]] = None
    articles: Optional[list[dict[str, Any]]] = None
    items: Optional[list[dict[str, Any]]] = Field(default=None, alias="list")

    def get_document_data(self) -> Optional[dict[str, Any]]:
        """
        Extract the document data from the appropriate wrapper.

        Returns:
            The unwrapped document data or None.
        """
        if self.article and isinstance(self.article, dict):
            return self.article
        if self.text and isinstance(self.text, dict):
            return self.text
        if self.acco and isinstance(self.acco, dict):
            return self.acco
        if self.result and isinstance(self.result, dict):
            return self.result
        # If no wrapper, return the model as dict (excluding None values)
        if self.id:
            result: dict[str, Any] = self.model_dump(
                exclude_none=True, exclude={"article", "text", "acco", "result"}
            )
            return result
        return None


# =============================================================================
# Validation helper functions
# =============================================================================


def validate_search_response(data: dict[str, Any]) -> SearchResponse:
    """
    Validate and parse a search response.

    Args:
        data: Raw API response data.

    Returns:
        Validated SearchResponse model.

    Raises:
        ValidationError: If validation fails.
    """
    return cast(SearchResponse, SearchResponse.model_validate(data))


def validate_oauth_response(data: dict[str, Any]) -> OAuthResponse:
    """
    Validate and parse an OAuth response.

    Args:
        data: Raw API response data.

    Returns:
        Validated OAuthResponse model.

    Raises:
        ValidationError: If validation fails.
    """
    return cast(OAuthResponse, OAuthResponse.model_validate(data))


def validate_code_list_response(data: dict[str, Any]) -> CodeListResponse:
    """
    Validate and parse a code list response.

    Args:
        data: Raw API response data.

    Returns:
        Validated CodeListResponse model.

    Raises:
        ValidationError: If validation fails.
    """
    return cast(CodeListResponse, CodeListResponse.model_validate(data))


def validate_document_response(data: dict[str, Any]) -> GenericDocumentResponse:
    """
    Validate and parse a document response.

    Args:
        data: Raw API response data.

    Returns:
        Validated GenericDocumentResponse model.

    Raises:
        ValidationError: If validation fails.
    """
    return cast(GenericDocumentResponse, GenericDocumentResponse.model_validate(data))
