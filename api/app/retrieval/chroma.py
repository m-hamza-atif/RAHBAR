"""Read-only Chroma retrieval and collection compatibility checks."""
from __future__ import annotations
import logging
import re
from typing import Any
from ..config import Settings
from ..embeddings import backend, embed_query
from ..schemas import Passage

log = logging.getLogger("rahbar.retrieval")


def version_scope(question: str) -> str:
    years = re.findall(r"\b(?:19|20)\d{2}\b", question)
    if years:
        if re.search(r"\b(before|after|since|between|compare)\b", question, re.I) or len(set(years)) > 1:
            return "historical"
        return years[0]
    return "historical" if re.search(
        r"\b(old policy|previous version|superseded|historical|previous policy)\b", question, re.I) else "current"


class ChromaRetriever:
    name = "chroma"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: Any = None

    @property
    def client(self) -> Any:
        if self._client is None:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            self._client = chromadb.HttpClient(host=self.settings.chroma_host,
                port=self.settings.chroma_port, settings=ChromaSettings(anonymized_telemetry=False))
        return self._client

    def collection(self) -> Any:
        return self.client.get_collection(self.settings.collection)

    def snapshot(self) -> str:
        collection = self.collection()
        meta = collection.metadata or {}
        conflicts = {
            "api_embed_model": self.settings.embed_model,
            "collection_embed_model": meta.get("embed_model"),
            "api_embed_dim": self.settings.embed_dim,
            "collection_embed_dim": meta.get("embed_dim"),
            "api_embedding_backend": backend(self.settings),
            "collection_embedding_backend": meta.get("embedding_backend"),
        }
        if (meta.get("embed_model") != self.settings.embed_model
                or meta.get("embed_dim") != self.settings.embed_dim
                or meta.get("embedding_backend") != backend(self.settings)):
            log.error("embedding_pin_mismatch", extra=conflicts)
            raise RuntimeError("embedding pin mismatch: " + str(conflicts))
        if meta.get("index_state") != "ready" or not meta.get("index_revision"):
            raise RuntimeError("Chroma index is building or has no ready revision")
        if collection.count() < 1:
            raise RuntimeError("Chroma collection is empty")
        return str(meta["index_revision"])

    def retrieve(self, question: str, k: int, embedding: list[float] | None = None) -> list[Passage]:
        self.snapshot()
        collection = self.collection()
        scope = version_scope(question)
        where: dict | None = {"superseded": False} if scope == "current" else None
        if scope.isdigit():
            # Metadata editions can be YYYY, YYYY-MM, or a report period.
            versions = {m["doc_version"] for m in collection.get(include=["metadatas"])["metadatas"]
                        if str(m.get("doc_version", "")).startswith(scope)}
            if not versions:
                return []
            where = {"doc_version": {"$in": sorted(versions)}}
        result = collection.query(query_embeddings=[embedding or embed_query(question, self.settings)],
            n_results=min(k, collection.count()), where=where,
            include=["documents", "metadatas", "distances"])
        passages = []
        for key, text, meta, distance in zip(result["ids"][0], result["documents"][0],
                                            result["metadatas"][0], result["distances"][0]):
            score = max(0.0, min(1.0, 1-float(distance)))
            passages.append(Passage(chunk_id=key, text=text, source=meta["source"],
                                    section=meta["section"], page=int(meta["page"]), score=score))
        return passages
