"""Page marker utilities for document traceability (RF-15, RNF-46)."""

from __future__ import annotations

import re

PAGE_MARKER = re.compile(r"<!--\s*PAGE:(\d+)\s*-->")


def page_marker(page_number: int) -> str:
    return f"\n<!-- PAGE:{page_number} -->\n"


def resolve_page_from_offset(text: str, offset: int) -> int | None:
    """Return the page number active at a character offset."""
    if offset < 0:
        return None
    current_page: int | None = None
    for match in PAGE_MARKER.finditer(text):
        if match.start() > offset:
            break
        current_page = int(match.group(1))
    return current_page


def resolve_page_from_snippet(text: str, snippet: str | None) -> int | None:
    if not snippet:
        return None
    normalized_snippet = " ".join(snippet.split())[:80]
    if len(normalized_snippet) < 12:
        return None
    lowered_text = text.lower()
    lowered_snippet = normalized_snippet.lower()
    index = lowered_text.find(lowered_snippet)
    if index < 0:
        return None
    return resolve_page_from_offset(text, index)
