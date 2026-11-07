# ADR 0001: index outside the API in a one-shot Job

Status: Partner A implementation complete; Kubernetes resources owned by Partner B.

The API may have three or more replicas and restart independently. Running PDF
extraction, OCR and embedding at API startup would duplicate expensive work,
create competing writers, delay readiness and repeat ingestion after crashes.
`indexer/pipeline/run.py` owns the five stages and exits zero only after a full
snapshot and semantic-cache invalidation complete. `api/app/main.py` only reads
collection metadata and dependency readiness; it never writes Chroma.

A Job gives indexing a separate lifecycle, retry policy and resource budget.
A CronJob can schedule refreshes without redeploying query replicas. A failed
rebuild leaves index_state=building, so API readiness fails closed until rerun.
Only after upserts, stale-ID removal, count verification and Redis invalidation
does storage publish ready. This is a maintenance readiness window, not an
atomic old-index/new-index swap. Model/dimension changes recreate the collection.

A Job object is not a distributed mutex. Partner B must prevent overlapping
writers: CronJob concurrencyPolicy=Forbid handles scheduled overlap, but manual
Jobs also need operational exclusion. API replicas remain readers of a single
Chroma server rather than direct competing writers to a database volume.

Alternatives: startup indexing was rejected for the races and restart cost;
a blue/green collection swap would preserve old-index availability but needs an
atomic active-index pointer and more storage. The simpler readiness window is
appropriate here. See docs/PIPELINE.md and indexer/pipeline/store.py.
