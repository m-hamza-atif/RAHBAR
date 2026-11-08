"""Prometheus metrics at /metrics (section 4.8).

Request count and latency are wired up already. Add your own the same way:
retrieval latency, generation latency, cache hits, abstentions, fallbacks, tokens.
"""

from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, Gauge, generate_latest

router = APIRouter()

REQUESTS = Counter("rahbar_requests_total", "HTTP requests", ["path", "status"])
LATENCY = Histogram(
    "rahbar_request_seconds",
    "HTTP request latency",
    ["path"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60),
)


@router.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

RETRIEVAL = Histogram("rahbar_retrieval_seconds", "Retrieval latency")
GENERATION = Histogram("rahbar_generation_seconds", "Generation latency")
CACHE_HITS = Counter("rahbar_cache_hits_total", "Semantic cache hits")
CACHE_MISSES = Counter("rahbar_cache_misses_total", "Semantic cache misses or skips")
CACHE_RATIO = Gauge("rahbar_cache_hit_ratio", "Process-local cache hit ratio")
ABSTENTIONS = Counter("rahbar_abstentions_total", "Honest abstentions")
FALLBACKS = Counter("rahbar_fallback_total", "Safe generation fallbacks")
PROMPT_TOKENS = Counter("rahbar_prompt_tokens_total", "Provider tokens or whitespace estimates")
COMPLETION_TOKENS = Counter("rahbar_completion_tokens_total", "Provider tokens or whitespace estimates")


def update_cache_ratio() -> None:
    hits = CACHE_HITS._value.get()
    total = hits + CACHE_MISSES._value.get()
    CACHE_RATIO.set(hits/total if total else 0)
