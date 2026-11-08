"""Stage 2: Clean. Remove artefacts without destroying structure."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import replace

from .models import Document


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("\u00ad", "").replace("\ufeff", "")
    text = re.sub(r"(?<=\w)-[ \t]*\n[ \t]*(?=[a-z])", "", text)
    text = "".join(c for c in text if c in "\n\t" or unicodedata.category(c) != "Cc")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def clean(doc: Document) -> Document:
    """Strip headers and footers that repeat on every page; keep headings and
    section boundaries, because chunking and citations depend on them."""
    return replace(doc, pages=[replace(p, text=clean_text(p.text)) for p in doc.pages])
