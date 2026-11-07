"""Section/paragraph/sentence chunking; units are whitespace tokens."""
from __future__ import annotations

import hashlib
import re

from .logging import log
from .models import Chunk, Document


def token_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def amplification(doc: Document, pieces: list[Chunk]) -> float:
    original = sum(token_count(p.text) for p in doc.pages)
    return sum(token_count(c.text) for c in pieces) / original if original else 0.0


def _sections(text: str, current: str) -> tuple[list[tuple[str, str]], str]:
    result: list[tuple[str, str]] = []
    lines: list[str] = []
    for line in text.splitlines():
        heading = re.match(r"^#{1,6}\s+(.+)", line)
        numbered = re.match(r"^\d+(?:\.\d+)*\.?\s+[A-Z].*", line)
        clause = re.fullmatch(r"\d+\.\d+(?:\.\d+)*", line.strip())
        words = line.split()
        title = (0 < len(words) <= 8 and all(
            word[:1].isupper() or word in {"of", "and", "the", "for", "under", "with"}
            for word in words) and not re.search(r"[.!?|]", line))
        if heading or clause or title or (
                numbered and token_count(line) <= 10 and not line.endswith('.')):
            if lines:
                result.append((current, '\n'.join(lines)))
            current = (heading.group(1).strip() if heading else
                       "Clause " + line.strip() if clause else line.strip())
            lines = [line]
        else:
            lines.append(line)
    if lines:
        result.append((current, '\n'.join(lines)))
    return result, current


def _windows(text: str, size: int, overlap: int, structured: bool):
    tokens = list(re.finditer(r"\S+", text))
    start = 0
    while start < len(tokens):
        end = min(start + size, len(tokens))
        if structured and end < len(tokens):
            # Prefer paragraph boundaries, then sentence boundaries; finally words.
            for pattern in (r"\n\s*\n", r"(?<=[.!?])\s+"):
                boundaries = [i for i in range(start + max(overlap + 1, size // 2), end + 1)
                              if re.search(pattern, text[tokens[i-1].end():tokens[i].start()]
                                           if pattern.startswith(r"\n") else
                                           text[tokens[i-1].start():tokens[i].start()])]
                if boundaries:
                    end = boundaries[-1]
                    break
        yield start, text[tokens[start].start():tokens[end-1].end()]
        if end == len(tokens):
            break
        start = end - overlap


def chunk(doc: Document, size: int, overlap: int,
          chunk_strategy: str = "structure") -> list[Chunk]:
    if not 0 <= overlap < size:
        raise ValueError("require 0 <= overlap < size")
    if chunk_strategy not in {"structure", "fixed"}:
        raise ValueError("unknown chunk strategy")
    pieces = []
    section = "Document"
    for page in doc.pages:
        sections, section = _sections(page.text, section)
        if chunk_strategy == "fixed":
            sections = [("Fixed window", page.text)]
        for index, (heading, text) in enumerate(sections):
            for offset, part in _windows(text, size, overlap, chunk_strategy == "structure"):
                identity = f"{doc.source}|{doc.doc_version}|{page.page}|{index}|{offset}|{part}"
                pieces.append(Chunk(hashlib.sha256(identity.encode()).hexdigest(), part,
                                    doc.source, heading, page.page, str(doc.doc_version),
                                    doc.superseded))
    log("chunking_summary", source=doc.source, chunks=len(pieces),
        storage_amplification=amplification(doc, pieces), size=size, overlap=overlap,
        strategy=chunk_strategy, token_unit="whitespace")
    return pieces
