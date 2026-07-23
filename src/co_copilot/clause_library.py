"""Loading and normalization for synthetic contractual clause excerpts."""

from __future__ import annotations

import re
from pathlib import Path


def load_clause_library(directory: Path) -> dict[str, str]:
    """Load clause files keyed by their normalized numeric reference."""
    library: dict[str, str] = {}
    for path in sorted(directory.glob("*.md")):
        text = path.read_text(encoding="utf-8").strip()
        match = re.search(r"#\s+(?:Sub-)?Clause\s+(\d+(?:\.\d+)*)", text, re.I)
        if match:
            library[match.group(1)] = text
    return library


def quote_clause(library: dict[str, str], reference: str) -> str | None:
    """Return the operative prose without the synthetic-note heading."""
    text = library.get(reference)
    if not text:
        return None
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n")]
    body = [
        paragraph for paragraph in paragraphs if not paragraph.startswith((">", "#"))
    ]
    return "\n\n".join(body) or text
