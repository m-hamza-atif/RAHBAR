"""Runtime configuration, read once from environment variables.

On the cluster these variables come from your ConfigMap and Secret (section 4.1).
Nothing here is baked into the image, so one image runs in every environment.
Add your own keys (relevance floor, cache settings, ...) the same way.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit


def _int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


def _float(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


@dataclass(frozen=True)
class Settings:
    # Which implementations to load. "stub" needs no cluster, no model, no network.
    retriever: str = "stub"          # RETRIEVER: stub | chroma
    llm_provider: str = "stub"       # LLM_PROVIDER: stub | ollama-host | ollama-incluster | hosted

    # The embedding pin (section 4.4). The indexer reads the same ConfigMap key.
    embed_model: str = "nomic-embed-text"

    # Vector store
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    collection: str = "rahbar_policies"

    # Retrieval and generation
    top_k: int = 5
    temperature: float = 0.1
    llm_model: str = "llama3.2:3b"
    ollama_url: str = "http://host.minikube.internal:11434"
    hosted_base_url: str = ""        # e.g. an OpenAI-compatible endpoint
    llm_api_key: str = field(default="", repr=False)   # from the Secret; never log it

    log_level: str = "INFO"
    embed_dim: int = 768
    redis_url: str = "redis://localhost:6379/0"
    redis_fake: bool = False
    relevance_floor: float = 0.35
    cache_threshold: float = 0.90
    cache_ttl: int = 3600


def get_settings() -> Settings:
    host = os.getenv("CHROMA_HOST", "localhost")
    parsed = urlsplit(host if "://" in host else "//" + host)
    stub = os.getenv("LLM_PROVIDER", "stub") == "stub" or os.getenv("EMBED_MODEL") == "stub"
    settings = Settings(
        retriever=os.environ.get("RETRIEVER", "stub"),
        llm_provider=os.environ.get("LLM_PROVIDER", "stub"),
        embed_model=os.environ.get("EMBED_MODEL", "nomic-embed-text"),
        chroma_host=parsed.hostname or host,
        chroma_port=parsed.port or _int("CHROMA_PORT", 8000),
        collection=os.environ.get("CHROMA_COLLECTION", "rahbar_policies"),
        top_k=_int("TOP_K", 5),
        temperature=_float("TEMPERATURE", 0.1),
        llm_model=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"
                            if os.getenv("LLM_PROVIDER") == "hosted" else "llama3.2:3b"),
        ollama_url=os.getenv("OLLAMA_BASE_URL", os.getenv(
            "OLLAMA_URL", "http://host.minikube.internal:11434")).rstrip("/"),
        hosted_base_url=os.environ.get("HOSTED_BASE_URL", ""),
        llm_api_key=os.environ.get("LLM_API_KEY", ""),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        embed_dim=_int("EMBED_DIM", 384 if stub else 768),
        redis_url=os.getenv("REDIS_URL") or (
            f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}/0"),
        redis_fake=os.getenv("REDIS_FAKE", "false").lower() == "true",
        relevance_floor=_float("RELEVANCE_FLOOR", .35),
        cache_threshold=_float("CACHE_THRESHOLD", .90),
        cache_ttl=_int("CACHE_TTL", 3600),
    )
    if not (0 <= settings.relevance_floor <= 1 and 0 <= settings.cache_threshold <= 1):
        raise ValueError("similarity thresholds must be between zero and one")
    if not 0 <= settings.temperature <= .3 or settings.top_k < 1 or settings.embed_dim < 1:
        raise ValueError("invalid temperature, TOP_K or EMBED_DIM")
    if settings.cache_ttl < 1:
        raise ValueError("CACHE_TTL must be positive")
    return settings
