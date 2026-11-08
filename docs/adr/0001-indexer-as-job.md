# ADR 0001: index outside the API in a one-shot Job

Status: implemented in the indexing pipeline and Kubernetes resources.

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

A Job object is not a distributed mutex. The deployment prevents overlapping
writers: CronJob concurrencyPolicy=Forbid handles scheduled overlap, but manual
Jobs also need operational exclusion. API replicas remain readers of a single
Chroma server rather than direct competing writers to a database volume.

Alternatives: startup indexing was rejected for the races and restart cost;
a blue/green collection swap would preserve old-index availability but needs an
atomic active-index pointer and more storage. The simpler readiness window is
appropriate here. See docs/PIPELINE.md and indexer/pipeline/store.py.

## Kubernetes implementation

The Job and CronJob are now implemented. Four reasons drive the separation:
(1) three startup writers race one collection; (2) pod crashes/scaling repeat OCR
and embedding costs; (3) query readiness waits for startup ingestion that itself
depends on unavailable data services; (4) operators need to reindex independently
of API deployments. `k8s/base/indexer.yaml:7` sets the bounded retry budget,
`k8s/base/reindex.yaml:9` forbids scheduled overlap, and `k8s/base/api.yaml:7`
requests three reader replicas. Rendered Job/CronJob specs are checked for equality.

`scripts/deploy.py:50` suspends the schedule and detects unfinished Jobs before
manual indexing. `indexer/entrypoint.py:15` obtains a renewable Redis writer lease
outside the invalidated cache prefix. Lease renewal failure terminates the child
writer. Do not restart Redis, clear its lease or suspend the writer host during
indexing: this is an operational lock, not consensus under arbitrary partitions.
Bootstrap waits for both data services before creating the one-shot Job.
