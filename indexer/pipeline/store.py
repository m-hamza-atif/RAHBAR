"""Only writer to Chroma; rebuild snapshot and invalidate semantic cache."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from .config import IndexerSettings
from .embed import validate_vectors
from .logging import log
from .models import Chunk


def get_client(settings: IndexerSettings) -> Any:
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    options = ChromaSettings(anonymized_telemetry=False)
    if settings.chroma_persist_dir:
        return chromadb.PersistentClient(path=settings.chroma_persist_dir, settings=options)
    return chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port,
                               settings=options)


def invalidate_cache(settings: IndexerSettings) -> int:
    import redis

    deleted = 0
    with redis.Redis.from_url(settings.redis_url, socket_timeout=5,
                              socket_connect_timeout=5) as client:
        client.ping()
        # SCAN is nonblocking; delete only our namespace, never FLUSHDB.
        for key in client.scan_iter(match="rahbar:cache:*", count=500):
            deleted += client.delete(key)
    log("cache_invalidated", deleted=deleted)
    return deleted


def store(chunks: list[Chunk], vectors: list[list[float]], settings: IndexerSettings) -> int:
    dimension = validate_vectors(vectors, len(chunks))
    if len({c.id for c in chunks}) != len(chunks):
        raise ValueError("duplicate chunk ids")
    client = get_client(settings)
    # Fail before changing the old index if Redis is unavailable.
    invalidate_cache(settings)
    collection = client.get_or_create_collection(
        name=settings.collection, metadata={"hnsw:space": "cosine"})
    # Chroma 1.0 rejects hnsw:space in modify(), even if its value is unchanged.
    # The distance configuration persists internally after creation.
    metadata = {k: v for k, v in (collection.metadata or {}).items()
                if not k.startswith("hnsw:")}
    metadata.update({"embed_model": settings.embed_model, "embed_dim": dimension,
                     "dimension": dimension, "index_state": "building",
                     "index_revision": uuid4().hex,
                     "embedding_backend": "stub" if settings.llm_provider == "stub"
                     or settings.embed_model == "stub" else "ollama"})
    old = {k: v for k, v in (collection.metadata or {}).items()
           if not k.startswith("hnsw:")}
    collection.modify(metadata={**old, "index_state": "building"})
    if collection.count() and (old.get("embed_model") != settings.embed_model
                               or old.get("embed_dim", old.get("dimension")) != dimension):
        client.delete_collection(settings.collection)
        collection = client.create_collection(
            name=settings.collection, metadata={"hnsw:space": "cosine", **metadata})
    else:
        collection.modify(metadata=metadata)
    for start in range(0, len(chunks), 100):
        batch = chunks[start:start+100]
        collection.upsert(ids=[c.id for c in batch], documents=[c.text for c in batch],
                          embeddings=vectors[start:start+100],
                          metadatas=[c.metadata() for c in batch])
    # Remove chunks no longer present after edits/removal or a chunking change.
    expected = {c.id for c in chunks}
    stale = [key for key in collection.get(include=[])["ids"] if key not in expected]
    for start in range(0, len(stale), 100):
        collection.delete(ids=stale[start:start+100])
    if collection.count() != len(chunks):
        raise RuntimeError("stored chunk count does not match the complete corpus")
    invalidate_cache(settings)
    collection.modify(metadata={**metadata, "index_state": "ready"})
    log("stored", chunks=len(chunks), embed_model=settings.embed_model,
        embed_dim=dimension, stale_deleted=len(stale), cache_invalidation="success")
    return len(chunks)
