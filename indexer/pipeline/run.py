"""The indexer Job's entry point. It runs once and exits (section 4.2).

    python -m pipeline.run --dummy    # week 1: three fake chunks, no model needed
    python -m pipeline.run            # the real pipeline: extract, clean, chunk, embed, store

Exit code 0 means the index was written; anything else fails the Job, and
Kubernetes retries it up to the Job's backoffLimit.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import replace
from pathlib import Path

from .config import IndexerSettings, get_settings
from .models import Chunk
from .logging import configure_logging, log


def _front_matter(path: Path) -> dict[str, str]:
    """Read `key: value` lines between leading '---' markers (used by eval/fixtures)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    meta: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta


def discover(corpus_dir: str) -> list[tuple[Path, str, bool]]:
    """List (path, doc_version, superseded) for every document to index.

    corpus/fetch.py writes _index.json next to the files it downloads; use it when
    present. Otherwise read Markdown front matter (the CI fixtures work this way).
    """
    root = Path(corpus_dir)
    index = root / "_index.json"
    if index.exists():
        entries = json.loads(index.read_text(encoding="utf-8"))
        return [(root / e["file"], str(e.get("doc_version", "unknown")),
                 bool(e.get("superseded", False))) for e in entries]
    found = []
    for path in sorted(root.glob("*")):
        if path.suffix.lower() not in {".pdf", ".md", ".html", ".txt"}:
            continue
        if path.name.lower().startswith("readme"):
            continue
        meta = _front_matter(path) if path.suffix.lower() == ".md" else {}
        found.append((path, meta.get("doc_version", "unknown"),
                      meta.get("superseded", "false").lower() == "true"))
    return found


def run_pipeline(settings: IndexerSettings) -> int:
    from .chunk import chunk, token_count
    from .clean import clean
    from .embed import embed
    from .extract import extract
    from .store import store

    documents = discover(settings.corpus_dir)
    if not documents:
        raise ValueError(f"no documents found in {settings.corpus_dir}")
    all_chunks: list[Chunk] = []
    original_tokens = 0
    ocr_pages = 0
    for path, doc_version, superseded in documents:
        doc = clean(extract(str(path), doc_version, superseded, settings.enable_ocr))
        original_tokens += sum(token_count(p.text) for p in doc.pages)
        ocr_pages += sum(p.ocr for p in doc.pages)
        pieces = chunk(doc, settings.chunk_size, settings.chunk_overlap, settings.chunk_strategy)
        log("chunked", source=path.name, chunks=len(pieces))
        all_chunks.extend(pieces)
    vectors, dimension = embed([c.text for c in all_chunks], settings)
    count = store(all_chunks, vectors, settings)
    log("pipeline_summary", chunks=count, ocr_pages=ocr_pages,
        storage_amplification=sum(token_count(c.text) for c in all_chunks) / original_tokens,
        embed_model=settings.embed_model, embed_dim=dimension, cache_invalidation="success")
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the RAHBAR index, then exit.")
    parser.add_argument("--dummy", action="store_true", help="write three fake chunks")
    args = parser.parse_args()
    configure_logging()
    try:
        settings = get_settings()
        if args.dummy:
            settings = replace(settings, embed_model="dummy-768", llm_provider="stub")
    except Exception as exc:
        log("configuration_failed", error=str(exc))
        return 1
    log("indexer starting", dummy=args.dummy, embed_model=settings.embed_model,
        collection=settings.collection, chroma=f"{settings.chroma_host}:{settings.chroma_port}",
        pod=os.environ.get("HOSTNAME", "-"))
    started = time.perf_counter()
    try:
        if args.dummy:
            from .dummy import DUMMY_CHUNKS, fake_vector
            from .store import store
            count = store(DUMMY_CHUNKS, [fake_vector(c.text) for c in DUMMY_CHUNKS], settings)
        else:
            count = run_pipeline(settings)
    except Exception as exc:
        log("indexer_failed", error=str(exc), error_type=type(exc).__name__)
        return 1
    log("indexer finished", chunks=count, seconds=round(time.perf_counter() - started, 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
