"""Liveness and readiness (section 4.3). They answer different questions."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Is the process alive? Must never touch Chroma, Redis or the LLM."""
    return {"status": "alive"}


@router.get("/readyz")
def readyz(request: Request, response: Response) -> dict[str, object]:
    from ..services.readiness import check
    checks, revision = check(request.app.state.retriever, request.app.state.cache)
    if not revision or len(revision) == 0:
        response.status_code = 503
    settings = request.app.state.settings
    configuration = {key: getattr(settings, key) for key in (
        'retriever', 'llm_provider', 'llm_model', 'embed_model', 'embed_dim',
        'collection', 'top_k', 'relevance_floor', 'cache_threshold')}
    return {"status": "ready" if revision else "not_ready", "checks": checks,
            "index_revision": revision or None, "configuration": configuration}
