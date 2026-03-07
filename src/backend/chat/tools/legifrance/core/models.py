"""Data models for Legifrance tools."""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..constants import (
    DEFAULT_NATURE_FALLBACK,
    DEFAULT_SECTION_TITLE,
    DEFAULT_TITLE_FALLBACK,
)
from ..exceptions import LegifranceDocumentNotFoundError, LegifranceParseError
from .text_utils import clean_text

logger = logging.getLogger(__name__)


@dataclass
class LegifranceSearchResult:
    """Represents a single search result from Legifrance."""

    id: str
    title: str
    text: str
    num: Optional[str] = None
    etat: Optional[str] = None
    nature: Optional[str] = None
    date_publication: Optional[str] = None
    date_signature: Optional[str] = None
    juridiction: Optional[str] = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class LegifranceCodeInfo:
    """Represents metadata about a legal code."""

    id: str
    title: str
    etat: Optional[str] = None
    cid: Optional[str] = None


@dataclass
class LegifranceDocument:
    """Represents a full legal document with its content and meta."""

    id: str
    title: str
    text: str
    date: str = ""
    url: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_raw(
        cls,
        data: dict[str, Any],
        document_id: str,
        url_builder: Callable[[str, str], str] | None = None,
    ) -> LegifranceDocument:
        """
        Construct a LegifranceDocument from raw API response.

        Args:
            data: Raw API response data.
            document_id: The document identifier.
            url_builder: Optional function to build URL from ID and fond.

        Returns:
            A LegifranceDocument instance.

        Raises:
            LegifranceDocumentNotFoundError: If document is null in response.
            LegifranceParseError: If response format is invalid.
        """
        if data is None:
            raise LegifranceDocumentNotFoundError(document_id)

        # Handle explicit null article in response
        if "article" in data and data["article"] is None:
            raise LegifranceDocumentNotFoundError(document_id, "API returned null article")

        # Safe unpacking strategy
        article = data.get("article") or data
        if isinstance(article, dict):
            # Unwrap result if "result" wrapper exists
            article = article.get("result") or article

        # Unwrap 'text' wrapper if present (common in JURI/Sandbox responses)
        if isinstance(article, dict) and "text" in article:
            text_data = article["text"]
            if isinstance(text_data, dict):
                if (
                    text_data.get("juridictionJudiciaire")
                    or text_data.get("idTechInjection")
                    or text_data.get("titre")
                ):
                    article = text_data

        # Handle ACCO (Accords d'entreprise) structure - has 'acco' wrapper
        if isinstance(article, dict) and "acco" in article:
            acco_data = article["acco"]
            if isinstance(acco_data, dict):
                article = acco_data

        if not isinstance(article, dict):
            raise LegifranceParseError(
                f"Invalid API response format for ID: {document_id}", raw_data=data
            )

        # Extract title
        title = cls._extract_title(article)

        # Extract date
        date_text = cls._extract_date(article)

        # Extract text content
        text_content = cls._extract_text(article)
        cleaned_text = clean_text(text_content)

        # Build URL
        url = ""
        if url_builder:
            url = url_builder(document_id, "UNKNOWN")

        return cls(
            id=document_id,
            title=title,
            text=cleaned_text,
            date=date_text,
            url=url,
            raw=data,
        )

    @classmethod
    def _extract_title(cls, article: dict[str, Any]) -> str:
        """Extract title from article data."""
        title = article.get("title") or article.get("titre") or article.get("titreTexte")

        # For LEGIARTI: build title from context if available
        if not title:
            text_titles = article.get("textTitles", [])
            if text_titles:
                code_name = text_titles[0].get("titre", "")
                art_num = article.get("num", "")
                section_title = article.get("sectionParentTitre", "")
                if code_name and art_num:
                    title = f"Article {art_num} - {code_name}"
                    if section_title:
                        title = f"Article {art_num} ({section_title}) - {code_name}"
                elif code_name:
                    title = code_name

        # Fallback construction from jurisprudence fields
        if not title:
            title = cls._build_fallback_title(article)

        return title or DEFAULT_TITLE_FALLBACK

    @classmethod
    def _build_fallback_title(cls, article: dict[str, Any]) -> str:
        """Build fallback title from jurisprudence fields."""
        parts = []

        jur = article.get("juridiction") or article.get("juridictionJudiciaire")
        if jur:
            parts.append(jur)

        chamber = article.get("chamber") or article.get("chambre")
        if chamber:
            parts.append(chamber)

        date_dec = article.get("dateDecision")
        relevant_date = article.get("relevantDate")
        if not date_dec and relevant_date is not None:
            try:
                ts = float(relevant_date)
                dt = datetime.datetime.fromtimestamp(ts / 1000)
                date_dec = dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError, OSError):
                pass
        if date_dec:
            parts.append(date_dec)

        num_aff = article.get("numeroAffaire") or article.get("numAffaire")
        if num_aff:
            parts.append(num_aff)

        return " - ".join(parts) if parts else ""

    @classmethod
    def _extract_date(cls, article: dict[str, Any]) -> str:
        """Extract date from article data."""
        date_text = (
            article.get("date")
            or article.get("dateTexte")
            or article.get("dateDecision")
            or article.get("jurisDate")
            or article.get("modifDate")
        )

        # Convert timestamp to date string if needed
        if date_text and isinstance(date_text, (int, float)):
            try:
                dt = datetime.datetime.fromtimestamp(date_text / 1000)
                date_text = dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError, OSError):
                date_text = None

        # For LEGIARTI: try to get dateDebut
        if not date_text and article.get("dateDebut"):
            try:
                ts = article.get("dateDebut")
                if isinstance(ts, (int, float)):
                    dt = datetime.datetime.fromtimestamp(ts / 1000)
                    date_text = dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError, OSError):
                pass

        # Fallback: check articleVersions for current version dateDebut
        if not date_text and article.get("articleVersions"):
            current_id = article.get("id") or article.get("idTechInjection")
            for ver in article.get("articleVersions", []):
                if ver.get("id") == current_id and ver.get("dateDebut"):
                    try:
                        ts = ver.get("dateDebut")
                        dt = datetime.datetime.fromtimestamp(ts / 1000)
                        date_text = dt.strftime("%Y-%m-%d")
                        break
                    except (ValueError, TypeError, OSError):
                        pass

        # Final fallback: relevantDate
        final_relevant_date = article.get("relevantDate")
        if not date_text and final_relevant_date is not None:
            try:
                ts = float(final_relevant_date)
                dt = datetime.datetime.fromtimestamp(ts / 1000)
                date_text = dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError, OSError):
                pass

        return date_text or ""

    @classmethod
    def _extract_text(cls, article: dict[str, Any]) -> str:
        """Extract text content from article data."""
        text_content: str = str(
            article.get("text") or article.get("texte") or article.get("content") or ""
        )

        # For ACCO documents: text is in attachment.content
        if not text_content:
            attachment = article.get("attachment")
            if isinstance(attachment, dict):
                text_content = str(attachment.get("content") or "")

        # Fallback for structured texts (Codes, Lois)
        if not text_content:
            if "sections" in article or "articles" in article:
                text_content = cls._build_structure_summary(article)
            elif "list" in article:
                list_items = article.get("list")
                list_count = len(list_items) if isinstance(list_items, list) else 0
                text_content = (
                    f"[Structure JORF]\nEléments: {list_count}\n(Ce document est un sommaire JORF.)"
                )

        return text_content

    @classmethod
    def _build_structure_summary(cls, article: dict[str, Any]) -> str:
        """Build a summary for structured documents (Codes, Lois)."""
        sections = article.get("sections", [])
        articles = article.get("articles", [])

        summary_parts = [f"[Structure Document - {article.get('nature', DEFAULT_NATURE_FALLBACK)}]"]
        summary_parts.append(f"Sections principales: {len(sections)}")
        summary_parts.append(f"Articles directs: {len(articles)}")

        # List first-level sections titles
        if sections:
            summary_parts.append("\nSommaire:")
            for sec in sections[:10]:
                sec_title = sec.get("title", DEFAULT_SECTION_TITLE)
                summary_parts.append(f"  - {sec_title}")
            if len(sections) > 10:
                summary_parts.append(f"  ... et {len(sections) - 10} autres sections")

        # If there are direct articles, list a few
        if articles:
            summary_parts.append("\nArticles:")
            for art in articles[:5]:
                art_num = art.get("num", "?")
                art_content = clean_text(art.get("content", ""))[:100]
                summary_parts.append(f"  - Art. {art_num}: {art_content}...")
            if len(articles) > 5:
                summary_parts.append(f"  ... et {len(articles) - 5} autres articles")

        summary_parts.append("\n(Utilisez la recherche pour trouver un article spécifique.)")
        return "\n".join(summary_parts)
