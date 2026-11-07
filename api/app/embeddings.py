"""Query embeddings matching the indexer; never indexes documents."""
import hashlib
import math
import re
import httpx
from .config import Settings


def backend(settings: Settings) -> str:
    return "stub" if settings.llm_provider == "stub" or settings.embed_model == "stub" else "ollama"


def embed_query(text: str, settings: Settings) -> list[float]:
    if backend(settings) == "stub":
        vector = [0.0] * 384
        for token in re.findall(r"\w+(?:\.\w+)*", text.lower()):
            digest = hashlib.sha256(token.encode()).digest()
            vector[int.from_bytes(digest[:4], "big") % 384] += 1 if digest[4] % 2 else -1
        norm = math.sqrt(sum(v*v for v in vector))
        if not norm:
            vector[0], norm = 1.0, 1.0
        return [v/norm for v in vector]
    urls = [settings.ollama_url]
    if settings.ollama_url == "http://host.minikube.internal:11434":
        urls.append("http://localhost:11434")
    with httpx.Client(timeout=60) as client:
        for index, url in enumerate(urls):
            try:
                response = client.post(url + "/api/embed", json={
                    "model": settings.embed_model, "input": [text], "truncate": False})
                response.raise_for_status()
                rows = response.json()["embeddings"]
                if len(rows) != 1:
                    raise ValueError("expected one query embedding")
                vector = rows[0]
                if (len(vector) != settings.embed_dim or not any(vector)
                        or not all(math.isfinite(x) for x in vector)):
                    raise ValueError("query embedding dimension/values mismatch")
                return list(vector)
            except httpx.TransportError:
                if index == len(urls) - 1:
                    raise
    raise RuntimeError("embedding endpoint unavailable")
