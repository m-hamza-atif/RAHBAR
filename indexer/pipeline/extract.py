"""Stage 1: Extract. PDF (or HTML, or Markdown) to text, page by page."""

from __future__ import annotations

import math
import re
import shutil
from collections import Counter
from dataclasses import replace
from html.parser import HTMLParser
from pathlib import Path

import pdfplumber
import pytesseract
from pdf2image import convert_from_path

from .logging import log
from .models import Document, Page


def strip_margins(pages: list[Page]) -> list[Page]:
    """Remove repeated edge lines, never numbered clauses/Markdown headings."""
    def eligible(line: str) -> bool:
        return bool(line and not re.match(r"^(?:#|\d+(?:\.\d+)+\b|\|)", line))

    edges: Counter[str] = Counter()
    for page in pages:
        lines = [x.strip() for x in page.text.splitlines() if x.strip()]
        edges.update({x for x in lines[:2] + lines[-2:] if eligible(x)})
    repeated = {x for x, count in edges.items()
                if count >= max(3, math.ceil(len(pages) * 0.6))}
    result = []
    for page in pages:
        lines = page.text.splitlines()
        nonempty = [i for i, line in enumerate(lines) if line.strip()]
        margins = set(nonempty[:2] + nonempty[-2:])
        text = "\n".join(line for i, line in enumerate(lines) if not (
            i in margins and (line.strip() in repeated or re.fullmatch(r"\s*\d+\s*", line))))
        result.append(replace(page, text=text))
    return result


def ocr_page(path: str, page: int) -> str:
    if not shutil.which("tesseract") or not shutil.which("pdftoppm"):
        raise RuntimeError("OCR requires tesseract-ocr and poppler-utils")
    images = convert_from_path(path, first_page=page, last_page=page, dpi=200)
    try:
        return str(pytesseract.image_to_string(images[0], lang="eng"))
    finally:
        for image in images:
            image.close()


def table_markdown(rows: list[list[str | None]]) -> str:
    def cell(value: str | None) -> str:
        return re.sub(r"\s+", " ", value or "").strip().replace("|", "\\|")
    if not rows:
        return ""
    width = max(map(len, rows))
    formatted = ["| " + " | ".join(cell(v) for v in row + [None] * (width - len(row)))
                 + " |" for row in rows]
    formatted.insert(1, "| " + " | ".join(["---"] * width) + " |")
    return "\n".join(formatted)


class PolicyHTML(HTMLParser):
    """Exclude navigation/scripts and preserve headings and table rows."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0
        self.rows: list[list[str | None]] = []
        self.row: list[str | None] = []
        self.cell: list[str] | None = None
        self.table = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "nav", "header", "footer"}:
            self.skip += 1
        if self.skip:
            return
        if tag == "table":
            self.table, self.rows = True, []
        elif tag == "tr":
            self.row = []
        elif tag in {"td", "th"}:
            self.cell = []
        elif re.fullmatch(r"h[1-6]", tag):
            self.parts.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag in {"p", "div", "li", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "nav", "header", "footer"}:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag in {"td", "th"} and self.cell is not None:
            self.row.append(" ".join(self.cell))
            self.cell = None
        elif tag == "tr" and self.row:
            self.rows.append(self.row)
        elif tag == "table":
            self.parts.append("\n\n" + table_markdown(self.rows) + "\n\n")
            self.table = False
        elif tag in {"p", "li"} or re.fullmatch(r"h[1-6]", tag):
            self.parts.append("\n\n")

    def handle_data(self, data: str) -> None:
        if self.skip:
            return
        if self.cell is not None:
            self.cell.append(data)
        elif not self.table:
            self.parts.append(data)


def extract(path: str, doc_version: str, superseded: bool,
            enable_ocr: bool = True) -> Document:
    file = Path(path)
    pages = []
    if file.suffix.lower() == ".pdf":
        with pdfplumber.open(file) as pdf:
            for number, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                used_ocr = False
                if len(re.sub(r"\s", "", text)) < 20:
                    if enable_ocr:
                        try:
                            recovered = ocr_page(path, number)
                            text = recovered if recovered.strip() else text
                            used_ocr = True
                            log("ocr_page", source=file.name, page=number, chars=len(text))
                        except (RuntimeError, pytesseract.TesseractNotFoundError) as exc:
                            log("ocr_unavailable", source=file.name, page=number,
                                loss="page text may be missing", error=str(exc))
                    else:
                        log("ocr_disabled", source=file.name, page=number,
                            loss="page text may be missing")
                elif tables := page.find_tables():
                    def outside_tables(obj: dict) -> bool:
                        return not any(t.bbox[0] <= obj.get("x0", -1) <= t.bbox[2]
                                       and t.bbox[1] <= obj.get("top", -1) <= t.bbox[3]
                                       for t in tables)
                    text = page.filter(outside_tables).extract_text() or ""
                    text += "\n\n" + "\n\n".join(table_markdown(t.extract()) for t in tables)
                pages.append(Page(file.name, number, text, used_ocr))
    elif file.suffix.lower() in {".html", ".htm"}:
        parser = PolicyHTML()
        parser.feed(file.read_text(encoding="utf-8"))
        pages = [Page(file.name, 1, "".join(parser.parts))]
    elif file.suffix.lower() in {".md", ".txt"}:
        text = file.read_text(encoding="utf-8")
        text = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.S)
        pages = [Page(file.name, 1, text)]
    else:
        raise ValueError(f"unsupported document: {file.suffix}")
    return Document(file.name, str(doc_version), superseded, strip_margins(pages))
