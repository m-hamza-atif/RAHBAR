"""Pinned Ollama embeddings and deterministic offline lexical hash vectors."""
from __future__ import annotations

import hashlib
import math
import re

import httpx

from .config import IndexerSettings
from .logging import log

STUB_DIM = 384


def stub_vector(text: str, dimension: int = STUB_DIM) -> list[float]:
    vector = [0.0] * dimension
    for token in re.findall(r"\w+(?:\.\w+)*", text.lower()):
        digest = hashlib.sha256(token.encode()).digest()
        vector[int.from_bytes(digest[:4], "big") % dimension] += 1 if digest[4] % 2 else -1
    norm = math.sqrt(sum(v*v for v in vector))
    if not norm:
        vector[0] = 1.0
        norm = 1.0
    return [v / norm for v in vector]


def validate_vectors(vectors: list[list[float]], count: int) -> int:
    if len(vectors) != count or not vectors or not vectors[0]:
        raise ValueError("embedding response count/dimension is invalid")
    dimension = len(vectors[0])
    if any(len(v) != dimension or not all(math.isfinite(x) for x in v)
           or not any(v) for v in vectors):
        raise ValueError("embeddings must have consistent dimensions, finite nonzero values")
    return dimension


def embed(texts: list[str], settings: IndexerSettings) -> tuple[list[list[float]], int]:
    if not texts:
        raise ValueError("cannot embed an empty corpus")
    backend = "stub" if settings.llm_provider == "stub" or settings.embed_model == "stub" else "ollama"
    vectors = []
    if backend == "stub":
        vectors = [stub_vector(text) for text in texts]
    else:
        urls = [settings.ollama_url]
        if settings.ollama_url == "http://host.minikube.internal:11434":
            urls.append("http://localhost:11434")
        with httpx.Client(timeout=120) as client:
            for start in range(0, len(texts), settings.embed_batch_size):
                for index, url in enumerate(urls):
                    try:
                        response = client.post(url + "/api/embed", json={
                            "model": settings.embed_model,
                            "input": texts[start:start + settings.embed_batch_size],
                            "truncate": False})
                        response.raise_for_status()
                        batch = response.json()["embeddings"]
                        validate_vectors(batch, len(texts[start:start + settings.embed_batch_size]))
                        vectors.extend(batch)
                        break
                    except httpx.TransportError:
                        if index == len(urls) - 1:
                            raise
    dimension = validate_vectors(vectors, len(texts))
    log("embedded", embed_model=settings.embed_model, embed_dim=dimension,
        embedding_backend=backend, chunks=len(vectors))
    return vectors, dimension
