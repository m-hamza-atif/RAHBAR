"""Indexer configuration, from the same ConfigMap the API reads (section 4.1)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class IndexerSettings:
    embed_model: str        # EMBED_MODEL: must equal the API's value (section 4.4)
    chroma_host: str
    chroma_port: int
    collection: str
    corpus_dir: str         # where the documents and _index.json sit inside the Job's pod
    chunk_size: int
    chunk_overlap: int
    ollama_url: str
    llm_provider: str = "ollama-host"
    redis_url: str = "redis://localhost:6379/0"
    chroma_persist_dir: str = ""
    chunk_strategy: str = "structure"
    enable_ocr: bool = True
    embed_batch_size: int = 32


def get_settings() -> IndexerSettings:
    host = os.getenv("CHROMA_HOST", "localhost")
    parsed = urlsplit(host if "://" in host else "//" + host)
    root = Path(__file__).resolve().parents[2] / "corpus" / "raw"
    settings = IndexerSettings(
        embed_model=os.environ.get("EMBED_MODEL", "nomic-embed-text"),
        chroma_host=parsed.hostname or host,
        chroma_port=parsed.port or int(os.environ.get("CHROMA_PORT", 8000)),
        collection=os.environ.get("CHROMA_COLLECTION", "rahbar_policies"),
        corpus_dir=os.environ.get("CORPUS_DIR", str(root)),
        chunk_size=int(os.environ.get("CHUNK_SIZE", 512)),
        chunk_overlap=int(os.environ.get("CHUNK_OVERLAP", 64)),
        ollama_url=os.getenv("OLLAMA_BASE_URL", os.getenv(
            "OLLAMA_URL", "http://host.minikube.internal:11434")).rstrip("/"),
        llm_provider=os.getenv("LLM_PROVIDER", "ollama-host"),
        redis_url=os.getenv("REDIS_URL") or (
            f"redis://{os.getenv('REDIS_HOST', 'localhost')}:"
            f"{os.getenv('REDIS_PORT', '6379')}/0"),
        chroma_persist_dir=os.getenv("CHROMA_PERSIST_DIR", ""),
        chunk_strategy=os.getenv("CHUNK_STRATEGY", "structure"),
        enable_ocr=os.getenv("ENABLE_OCR", "true").lower() == "true",
        embed_batch_size=int(os.getenv("EMBED_BATCH_SIZE", "32")),
    )
    if not 0 <= settings.chunk_overlap < settings.chunk_size:
        raise ValueError("require 0 <= CHUNK_OVERLAP < CHUNK_SIZE")
    if settings.chunk_strategy not in {"structure", "fixed"}:
        raise ValueError("CHUNK_STRATEGY must be structure or fixed")
    if settings.embed_batch_size < 1:
        raise ValueError("EMBED_BATCH_SIZE must be positive")
    return settings
