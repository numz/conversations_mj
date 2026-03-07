"""Result parsing utilities for Legifrance search results."""

from __future__ import annotations

from typing import Any, Optional

from ..constants import (
    ARTICLE_TITLE_FALLBACK,
    ID_PREFIX_ACCOTEXT,
    ID_PREFIX_CETATEXT,
    ID_PREFIX_CNILTEXT,
    ID_PREFIX_JORFTEXT,
    ID_PREFIX_JURITEXT,
    NO_TITLE_FALLBACK,
)
from .models import LegifranceSearchResult
from .text_utils import clean_text
from .urls import get_legifrance_url


def flatten_search_result(item: dict[str, Any]) -> list[LegifranceSearchResult]:
    """
    Recursively extract relevant items (articles, texts) from a hierarchical search result.

    Args:
        item: A single search result item from the API.

    Returns:
        List of flattened LegifranceSearchResult objects.
    """
    parsed_results: list[LegifranceSearchResult] = []

    # Extract metadata to carry down from the root item
    meta = {
        "nature": item.get("nature"),
        "etat": item.get("etat"),
        "date_publication": item.get("datePublication"),
        "date_signature": item.get("dateSignature"),
        "juridiction": item.get("juridiction"),
    }
    meta = {k: v for k, v in meta.items() if v}

    root_id = item.get("id")
    if not root_id and "titles" in item and item["titles"]:
        root_id = item["titles"][0].get("id")

    def _recursive_extract(node: dict[str, Any], inherited_meta: dict[str, Any]) -> bool:
        found = False

        # 1. Look for 'extracts' (matches with snippets)
        if "extracts" in node:
            for extract in node["extracts"]:
                t = extract.get("title", extract.get("titre", NO_TITLE_FALLBACK))
                snippet_raw = " ".join(extract.get("values", []))

                fallback_id = extract.get("id") or node.get("id") or root_id

                entry_data: dict[str, Any] = {
                    "id": fallback_id,
                    "num": extract.get("num"),
                    "title": t,
                    "text": clean_text(snippet_raw),
                }

                # Dynamic extraction of other fields
                for k, v in extract.items():
                    if k not in ["id", "num", "title", "titre", "values"] and v:
                        entry_data[k] = v

                entry_data.update(inherited_meta)

                # Filter valid fields for dataclass
                valid_fields = [
                    "id",
                    "title",
                    "text",
                    "num",
                    "etat",
                    "nature",
                    "date_publication",
                    "date_signature",
                    "juridiction",
                ]
                dataclass_kwargs = {k: v for k, v in entry_data.items() if k in valid_fields}

                parsed_results.append(LegifranceSearchResult(**dataclass_kwargs))
                found = True

        # 2. Look for 'list' (sometimes for JORF/LODA files)
        if "list" in node:
            for sub in node["list"]:
                t = sub.get("title", sub.get("titre", NO_TITLE_FALLBACK))
                text_raw = sub.get("text", "")[:300]
                entry_data = {
                    "id": sub.get("id"),
                    "num": sub.get("num"),
                    "title": t,
                    "text": clean_text(text_raw),
                }

                # Dynamic extraction
                for k, v in sub.items():
                    if k not in ["id", "num", "title", "titre", "text"] and v:
                        entry_data[k] = v

                entry_data.update(inherited_meta)

                # Filter valid fields for dataclass
                valid_fields = [
                    "id",
                    "title",
                    "text",
                    "num",
                    "etat",
                    "nature",
                    "date_publication",
                    "date_signature",
                    "juridiction",
                ]
                dataclass_kwargs = {k: v for k, v in entry_data.items() if k in valid_fields}

                parsed_results.append(LegifranceSearchResult(**dataclass_kwargs))
                found = True

        # 3. Recurse into sections
        if "sections" in node:
            for section in node["sections"]:
                if _recursive_extract(section, inherited_meta):
                    found = True

        return found

    # Determine if we should force flat extraction
    force_flat = False
    if "titles" in item and item["titles"]:
        first_id = item["titles"][0].get("id", "")
        if first_id.startswith(
            (
                ID_PREFIX_JURITEXT,
                ID_PREFIX_CETATEXT,
                ID_PREFIX_ACCOTEXT,
                ID_PREFIX_CNILTEXT,
                ID_PREFIX_JORFTEXT,
            )
        ):
            force_flat = True

    # KALI (and other fonds) can include relevant extracts inside sections
    # If sections contain extracts, prefer recursive extraction over flat fallback
    if force_flat and item.get("sections"):
        for section in item.get("sections", []):
            if isinstance(section, dict) and section.get("extracts"):
                force_flat = False
                break

    # Also allow recursive extraction if there's a 'list' (JORF style)
    if force_flat and item.get("list"):
        force_flat = False

    found_nested = False
    if not force_flat:
        found_nested = _recursive_extract(item, meta)

    if not found_nested:
        # Fallback: Treat the item itself as the result (Flat result like JURI)
        main_title = NO_TITLE_FALLBACK
        main_id = item.get("id")

        if "titles" in item and item["titles"]:
            first_title = item["titles"][0]
            main_title = first_title.get("title", NO_TITLE_FALLBACK)
            if not main_id:
                main_id = first_title.get("id")
        elif "title" in item:
            main_title = item["title"]
        elif "titre" in item:
            main_title = item["titre"]

        snippet = item.get("content", item.get("text", item.get("etat", "")))

        parsed_results.append(
            LegifranceSearchResult(
                id=main_id or "",
                num=item.get("num"),
                title=main_title,
                text=clean_text(snippet),
                etat=meta.get("etat") or item.get("etat"),
                nature=meta.get("nature") or item.get("nature"),
                date_publication=meta.get("date_publication") or item.get("datePublication"),
                date_signature=meta.get("date_signature") or item.get("dateSignature"),
                juridiction=meta.get("juridiction") or item.get("juridiction"),
                raw=item,
            )
        )

    return parsed_results


def format_result_item(
    r: LegifranceSearchResult,
    fond: str,
    extra_meta: Optional[list[str]] = None,
) -> str:
    """
    Format a single result item for display.

    Args:
        r: The search result to format.
        fond: The document source (fond).
        extra_meta: Additional metadata strings to include.

    Returns:
        Formatted string representation of the result.
    """
    if extra_meta is None:
        extra_meta = []

    rid = r.id
    url = get_legifrance_url(rid, fond)

    title = r.title or ARTICLE_TITLE_FALLBACK
    if r.num:
        title = f"{title} (article: {r.num})"

    snippet = r.text

    # Common Metadata
    meta_parts = []
    if r.etat:
        meta_parts.append(f"Etat: {r.etat}")

    # Add tool specific metadata
    meta_parts.extend(extra_meta)

    meta_str = " | ".join(meta_parts)
    if meta_str:
        meta_str = f"  ({meta_str})"

    if url:
        return f"- {title} (ID: {rid}){meta_str}\n  Lien: {url}\n  Texte: {snippet}"
    else:
        return f"- {title} (ID: {rid}){meta_str}:\n Texte: {snippet}"
