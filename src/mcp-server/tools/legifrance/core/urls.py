"""URL generation utilities for Legifrance documents."""

from __future__ import annotations

from ..constants import (
    FOND_ACCO,
    FOND_CETAT,
    FOND_CIRC,
    FOND_CNIL,
    FOND_CONSTIT,
    FOND_JORF,
    FOND_JUFI,
    FOND_JURI,
    FOND_PREFIX_LODA,
    ID_PREFIX_ACCOTEXT,
    ID_PREFIX_CEHR,
    ID_PREFIX_CETATEXT,
    ID_PREFIX_CNILTEXT,
    ID_PREFIX_CONSTEXT,
    ID_PREFIX_JORFARTI,
    ID_PREFIX_JORFTEXT,
    ID_PREFIX_JUFITEXT,
    ID_PREFIX_JURITEXT,
    ID_PREFIX_KALIARTI,
    ID_PREFIX_KALITEXT,
    ID_PREFIX_LEGIARTI,
    ID_PREFIX_LEGITEXT,
    LEGIFRANCE_UI_BASE_URL,
    UI_PATH_ACCO,
    UI_PATH_CETA,
    UI_PATH_CIRC,
    UI_PATH_CNIL,
    UI_PATH_CODES_ARTICLE,
    UI_PATH_CODES_TEXTE,
    UI_PATH_CONS,
    UI_PATH_CONV_COLL,
    UI_PATH_CONV_COLL_ARTICLE,
    UI_PATH_JUFI,
    UI_PATH_JORF,
    UI_PATH_JURI,
    UI_PATH_LODA,
)


def get_legifrance_url(rid: str, fond: str) -> str:
    """
    Generate Legifrance UI URL based on ID and Fond.

    Args:
        rid: The document identifier.
        fond: The document source (fond).

    Returns:
        The Legifrance web URL for the document, or empty string if unknown.
    """
    if not rid:
        return ""

    # Check by ID prefix first (more specific)
    if rid.startswith(ID_PREFIX_LEGIARTI):
        return f"{LEGIFRANCE_UI_BASE_URL}/{UI_PATH_CODES_ARTICLE}/{rid}"

    if rid.startswith(ID_PREFIX_LEGITEXT):
        return f"{LEGIFRANCE_UI_BASE_URL}/{UI_PATH_CODES_TEXTE}/{rid}"

    if rid.startswith(ID_PREFIX_JURITEXT) or fond == FOND_JURI:
        return f"{LEGIFRANCE_UI_BASE_URL}/{UI_PATH_JURI}/{rid}"

    if rid.startswith(ID_PREFIX_JUFITEXT) or fond == FOND_JUFI:
        return f"{LEGIFRANCE_UI_BASE_URL}/{UI_PATH_JUFI}/{rid}"

    if rid.startswith(ID_PREFIX_CNILTEXT) or fond == FOND_CNIL:
        return f"{LEGIFRANCE_UI_BASE_URL}/{UI_PATH_CNIL}/{rid}"

    if rid.startswith(ID_PREFIX_ACCOTEXT) or fond == FOND_ACCO:
        return f"{LEGIFRANCE_UI_BASE_URL}/{UI_PATH_ACCO}/{rid}"

    if fond == FOND_CIRC:
        return f"{LEGIFRANCE_UI_BASE_URL}/{UI_PATH_CIRC}/{rid}"

    if fond.startswith(FOND_PREFIX_LODA):
        return f"{LEGIFRANCE_UI_BASE_URL}/{UI_PATH_LODA}/{rid}"

    if fond == FOND_JORF or rid.startswith(ID_PREFIX_JORFTEXT):
        return f"{LEGIFRANCE_UI_BASE_URL}/{UI_PATH_JORF}/{rid}"

    if rid.startswith(ID_PREFIX_JORFARTI):
        return f"{LEGIFRANCE_UI_BASE_URL}/{UI_PATH_JORF}/{rid}"

    if fond == FOND_CONSTIT:
        return f"{LEGIFRANCE_UI_BASE_URL}/{UI_PATH_CONS}/{rid}"

    if rid.startswith(ID_PREFIX_CONSTEXT):
        return f"{LEGIFRANCE_UI_BASE_URL}/{UI_PATH_CONS}/{rid}"

    if rid.startswith(ID_PREFIX_KALITEXT):
        return f"{LEGIFRANCE_UI_BASE_URL}/{UI_PATH_CONV_COLL}/{rid}"

    if rid.startswith(ID_PREFIX_KALIARTI):
        return f"{LEGIFRANCE_UI_BASE_URL}/{UI_PATH_CONV_COLL_ARTICLE}/{rid}"

    if (
        fond == FOND_CETAT
        or rid.startswith(ID_PREFIX_CETATEXT)
        or rid.startswith(ID_PREFIX_CEHR)
    ):
        return f"{LEGIFRANCE_UI_BASE_URL}/{UI_PATH_CETA}/{rid}"

    return ""


def extract_context_from_raw(raw_data: dict | None) -> str | None:
    """
    Extract context (code name, text title) from raw search result data.

    Args:
        raw_data: Raw API response data from a search result.

    Returns:
        Context string (e.g., "Code du travail") or None if not found.
    """
    if not raw_data:
        return None

    # Try to extract from titles array (common in search results)
    titles = raw_data.get("titles", [])
    if titles and isinstance(titles, list):
        first_title = titles[0]
        if isinstance(first_title, dict):
            title_text = first_title.get("title") or first_title.get("titre")
            if title_text and title_text not in ("Sans titre", "NO_TITLE", "No Title"):
                return title_text

    # Try to extract from textTitles (common in article data)
    text_titles = raw_data.get("textTitles", [])
    if text_titles and isinstance(text_titles, list):
        first_text_title = text_titles[0]
        if isinstance(first_text_title, dict):
            title_text = first_text_title.get("titre") or first_text_title.get("title")
            if title_text:
                return title_text

    # Try to extract NOR for JORF documents
    nor = raw_data.get("nor") or raw_data.get("NOR")
    if nor:
        return f"NOR: {nor}"

    # Try to extract from parent title
    parent_title = raw_data.get("titreTexte") or raw_data.get("textTitle")
    if parent_title:
        return parent_title

    return None


def build_source_with_title(
    rid: str,
    fond: str,
    title: str | None = None,
    num: str | None = None,
    etat: str | None = None,
    context: str | None = None,
    raw_data: dict | None = None,
) -> tuple[str, str] | None:
    """
    Build a source tuple (url, title) for a Legifrance document.

    Args:
        rid: The document identifier.
        fond: The document source (fond).
        title: Optional title of the document.
        num: Optional article number.
        etat: Optional status of the text (VIGUEUR, ABROGE, etc.).
        context: Optional context (e.g., code name, convention name).
        raw_data: Optional raw API response to extract context from.

    Returns:
        A tuple (url, display_title) or None if URL cannot be generated.
    """
    url = get_legifrance_url(rid, fond)
    if not url:
        return None

    # Try to extract context from raw data if not provided
    effective_context = context
    if not effective_context and raw_data:
        effective_context = extract_context_from_raw(raw_data)

    # Build a meaningful display title
    display_title = _build_display_title(rid, title, num, etat, effective_context)

    return (url, display_title)


def _build_display_title(
    rid: str,
    title: str | None,
    num: str | None,
    etat: str | None,
    context: str | None = None,
) -> str:
    """Build a meaningful display title for a source."""
    # Clean up title - remove redundant parts
    clean_title = title
    if title and title not in ("Sans titre", "NO_TITLE", "No Title"):
        # If title already contains the article number, don't repeat it
        if num and num in title:
            clean_title = title
        else:
            clean_title = title
    else:
        clean_title = None

    # Build the display title
    if num:
        # For articles, prioritize the article number with context
        if clean_title and clean_title != num:
            # Truncate long titles
            if len(clean_title) > 50:
                clean_title = clean_title[:47] + "..."
            display_title = f"Art. {num} - {clean_title}"
        elif context:
            # Use context (e.g., code name) if available
            display_title = f"Article {num} du {context}"
        else:
            display_title = f"Article {num}"
    elif clean_title:
        # Truncate long titles
        if len(clean_title) > 60:
            clean_title = clean_title[:57] + "..."
        display_title = clean_title
    else:
        # Fallback: extract document type from ID prefix
        display_title = _get_document_type_label(rid)

    # Add status indicator for non-current texts
    if etat and etat.upper() not in ("VIGUEUR", "EN_VIGUEUR", "EN VIGUEUR"):
        etat_label = _get_etat_label(etat)
        if etat_label:
            display_title = f"{display_title} [{etat_label}]"

    return display_title


def _get_etat_label(etat: str) -> str:
    """Get a short label for the document status."""
    etat_upper = etat.upper()
    if "ABROGE" in etat_upper:
        return "Abrogé"
    if "MODIFIE" in etat_upper:
        return "Modifié"
    if "PERIME" in etat_upper:
        return "Périmé"
    if "ANNULE" in etat_upper:
        return "Annulé"
    return ""


def _get_document_type_label(rid: str) -> str:
    """Get a human-readable label for a document based on its ID prefix."""
    if rid.startswith(ID_PREFIX_LEGIARTI):
        return "Article de Code"
    if rid.startswith(ID_PREFIX_LEGITEXT):
        return "Code"
    if rid.startswith(ID_PREFIX_JURITEXT):
        return "Décision de justice"
    if rid.startswith(ID_PREFIX_JUFITEXT):
        return "Décision financière"
    if rid.startswith(ID_PREFIX_CETATEXT):
        return "Décision admin."
    if rid.startswith(ID_PREFIX_CNILTEXT):
        return "Délibération CNIL"
    if rid.startswith(ID_PREFIX_ACCOTEXT):
        return "Accord collectif"
    if rid.startswith(ID_PREFIX_JORFTEXT):
        return "Texte JORF"
    if rid.startswith(ID_PREFIX_JORFARTI):
        return "Article JORF"
    if rid.startswith(ID_PREFIX_KALITEXT):
        return "Convention collective"
    if rid.startswith(ID_PREFIX_KALIARTI):
        return "Article convention"
    if rid.startswith(ID_PREFIX_CONSTEXT):
        return "Décision constitutionnelle"
    return "Document Légifrance"
