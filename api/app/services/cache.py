"""Redis semantic cache. Memory is allowed only when REDIS_FAKE=true."""
from __future__ import annotations
import hashlib
import json
import math
import re
import time
from typing import Any
import redis
from ..config import Settings
from ..schemas import AskResponse
from ..retrieval.chroma import version_scope


def follow_up(question: str, history: list) -> bool:
    return bool(history) or bool(re.search(r"\b(it|its|they|them|those|their)\b", question, re.I)) or bool(re.match(
        r"^\s*(and\b|also\b|what about\b|how about\b|that\b|those\b|it\b|they\b|then\b|why\s+is\s+that)",
        question, re.I))


def never_cache(question: str, history: list, response: AskResponse | None = None) -> bool:
    """Never-cache rule: follow-ups and unverified abstentions are never cached."""
    if follow_up(question, history):
        return True
    if response is not None and (not response.answered_from_context or not response.citations):
        return True
    return False


def cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return -1
    norm = math.sqrt(sum(v*v for v in a)*sum(v*v for v in b))
    return sum(x*y for x, y in zip(a, b))/norm if norm else -1


def scope(question: str) -> str:
    # Do not reuse an answer across explicit years/numbers or opposite negation.
    return json.dumps([version_scope(question), re.findall(r"\d+(?:\.\d+)*", question),
                       bool(re.search(r"\b(not|never|without|except)\b", question, re.I))])


class SemanticCache:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.memory: dict[str, dict[str, Any]] = {}
        self.client = None if settings.redis_fake else redis.Redis.from_url(
            settings.redis_url, socket_timeout=3, socket_connect_timeout=3)

    def ping(self) -> bool:
        return bool(self.client.ping()) if self.client is not None else True

    def close(self) -> None:
        if self.client is not None:
            self.client.close()

    def namespace(self, revision: str) -> str:
        s = self.settings
        identity = ["cache-v1", s.collection, revision, s.embed_model, s.embed_dim, s.llm_provider,
                    s.llm_model, s.top_k, s.relevance_floor, s.temperature]
        return 'rahbar:cache:' + hashlib.sha256(json.dumps(identity).encode()).hexdigest() + ':'

    def find(self, question: str, vector: list[float], revision: str) -> AskResponse | None:
        prefix = self.namespace(revision)
        if self.client is None:
            entries = [v for k, v in self.memory.items() if k.startswith(prefix)]
        else:
            entries = []
            for key in self.client.scan_iter(match=prefix+'*', count=100):
                value = self.client.get(key)
                if isinstance(value, (str, bytes)):
                    try:
                        entries.append(json.loads(value))
                    except (ValueError, TypeError):
                        continue
                if len(entries) >= 256:
                    break
        best, result = -1.0, None
        for entry in entries:
            try:
                if time.time()-entry['timestamp'] >= self.settings.cache_ttl:
                    continue
                if scope(question) != scope(entry['query_text']):
                    continue
                similarity = cosine(vector, entry['query_embedding'])
                if similarity >= self.settings.cache_threshold and similarity > best:
                    candidate = AskResponse.model_validate(entry['response_json'])
                    refs = {(p.source, p.section, p.page) for p in candidate.retrieved}
                    if (not candidate.answered_from_context or not candidate.citations
                            or any((c.source, c.section, c.page) not in refs for c in candidate.citations)):
                        continue
                    best, result = similarity, candidate
            except (ValueError, TypeError, KeyError):
                continue
        return result

    def put(self, question: str, vector: list[float], revision: str, response: AskResponse) -> None:
        if not response.answered_from_context or not response.citations:
            return
        entry = dict(query_text=question, query_embedding=vector,
                     response_json=response.model_dump(), timestamp=time.time())
        key = self.namespace(revision) + hashlib.sha256(question.encode()).hexdigest()
        if self.client is None:
            if len(self.memory) >= 256:
                self.memory.pop(next(iter(self.memory)))
            self.memory[key] = entry
        else:
            self.client.set(key, json.dumps(entry), ex=self.settings.cache_ttl)

    def invalidate(self, revision: str | None = None) -> int:
        """Invalidate cache keys for a specific revision or flush all namespaces."""
        if self.client is None:
            count = len(self.memory)
            self.memory.clear()
            return count
        pattern = self.namespace(revision) + '*' if revision else 'rahbar:cache:*'
        keys = list(self.client.scan_iter(match=pattern, count=100))
        if keys:
            return self.client.delete(*keys)
        return 0

    def clear_cache(self) -> int:
        return self.invalidate()
