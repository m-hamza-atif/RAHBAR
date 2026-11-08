"""Read-only dependency checks shared by startup, readiness and queries."""
from typing import Any
import logging

log = logging.getLogger('rahbar.readiness')


def check(retriever: Any, cache: Any) -> tuple[dict[str, str], str]:
    checks = {}
    revision = ''
    try:
        revision = retriever.snapshot()
        checks['chroma'] = 'ok' if retriever.name == 'chroma' else 'stub (no external index)'
    except Exception as exc:
        checks['chroma'] = str(exc)
    try:
        if not cache.ping():
            raise RuntimeError('Redis ping failed')
        checks['redis'] = 'ok'
    except Exception as exc:
        checks['redis'] = 'Redis unavailable: ' + type(exc).__name__
    if not revision or checks['redis'] != 'ok':
        log.error('readiness_failed', extra={'checks': checks})
    return checks, revision if checks['redis'] == 'ok' else ''
