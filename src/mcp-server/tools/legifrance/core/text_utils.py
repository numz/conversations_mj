"""Text utilities for Legifrance tools."""

from __future__ import annotations

import re
from typing import Any


def clean_text(text: Any) -> str:
    """Strip HTML tags and unescape entities.

    Args:
        text: The text to clean, can be any type.

    Returns:
        Cleaned text with HTML tags removed and entities unescaped.
    """
    if not text:
        return ""

    # Defense against non-string inputs (e.g. dicts from API)
    if not isinstance(text, str):
        return str(text)

    # 0. Normalize newlines
    clean = text.replace("\r\n", "\n")

    # 1. Replace structural tags with newlines/markdown
    clean = re.sub(r"<br\s*/?>", "\n", clean, flags=re.IGNORECASE)
    clean = re.sub(r"</?p\s*>", "\n\n", clean, flags=re.IGNORECASE)
    clean = re.sub(r"<li\s*>", "\n- ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"</?ul\s*>", "\n", clean, flags=re.IGNORECASE)
    clean = re.sub(r"</?div\s*>", "\n", clean, flags=re.IGNORECASE)

    # 2. Remove other HTML tags
    clean = re.sub(r"<[^>]+>", "", clean)

    # 3. Unescape HTML entities
    clean = (
        clean.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )
    clean = clean.replace("&#39;", "'").replace("&quot;", '"')

    # 4. Collapse multiple newlines
    clean = re.sub(r"\n{3,}", "\n\n", clean)

    return clean.strip()
