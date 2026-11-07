# Engineering notes ? Partner A implementation and Partner B handoff

These notes distinguish implemented local behavior from cluster evidence that
must be supplied after Partner B merges the Kubernetes track. File/line references
below were generated from this checkout, not guessed manifest filenames/lines.

## 1. Indexing in API startup with three replicas and one Chroma volume

The query process only reads an existing collection. Its lifespan constructs
retriever/provider/cache objects and runs read-only readiness checks:
`api/app/main.py:29`. The one-shot writer is
`indexer/pipeline/run.py:63` and collection writes occur in
`indexer/pipeline/store.py:38`. Three API replicas therefore do
not each OCR/embed/write the corpus. Startup ingestion would repeat expensive
work, create conflicting rebuilds and keep replicas unready while they attempt
to construct their own prerequisite. A Job separates indexing resources/lifecycle
from query serving. A Job itself does not serialize other Jobs: forbid scheduled
overlap and coordinate manual reindexes. Actual Job/CronJob manifest line numbers
remain Partner B evidence, not invented here.

## 2. Swapped liveness/readiness and a 90-second Chroma stall

`api/app/routes/health.py:11` touches no dependency; readiness
uses `api/app/services/readiness.py:8` and
`api/app/retrieval/chroma.py:42`. Dependency failure returns
503 only for readiness/query while liveness stays 200, verified with a real model
pin mismatch. Swapping probe URLs would make a dependency stall restart healthy
API processes while allowing nonfunctional ones to receive traffic.

Illustration using the proposed liveness period=20 seconds, failureThreshold=3:
three consecutive failures can trigger a restart after roughly 40-60 seconds,
depending on probe phase and timeout. Across three replicas this risks correlated
restarts during a 90-second shared outage. It is not correct to calculate an exact
restart total from 90/20 alone: startup probes, deadlines and backoff matter.
Partner B must replace these proposed values with deployed manifest line references.

## 3. CPU HPA and the 8% paradox

A CPU-utilization target is relative to requested CPU, not a direct measurement
of users waiting for an external LLM. Three replicas at 8% against a 70% target
would suggest ceil(3*8/70)=1 replica before the minimum-three constraint. An
I/O-bound API can have high latency while consuming little CPU. Request/generation
latency and cache metrics live in `api/app/routes/metrics.py:28`.
A stronger autoscaling design would expose in-flight generation or queue depth
through a Prometheus adapter/KEDA and bound concurrency. That custom scaling
signal is a recommendation, not an already deployed component. Cluster HPA
readings and manifest line references are Partner B's remaining evidence.

## 4. Memory, limits, margin and exit 137

Real local GNU time measurements for full-corpus WSL indexing with OCR and stub
vectors: peak RSS fell from 1,083,120 KiB to 165,492 KiB (161.6 MiB) after
`indexer/pipeline/extract.py:153` explicitly released
retained PDF layouts. Both runs exited zero. Ollama is external and its memory is
not included. These are not Kubernetes pod peaks. The exact container memory
limit and peak under the deployed image remain unmeasured until Partner B runs
`kubectl top pods -n rahbar` while the indexer is active and records limits from
the applied manifests. Margin = configured limit - measured peak in the same units.

Exit 137 means SIGKILL (128+9), not automatically proof of OOM. Check pod status
reason OOMKilled and events/logs to distinguish memory exhaustion from another
kill. A thin client avoids loading the embedding model in the indexer container,
but PDF layouts/OCR images still need a tested resource budget.

## 5. Recall by question type: the weakest category and why

The frozen full set has nine ordinary, two version-sensitive, four exact-term,
two must-abstain and one injection question. The measured retrieval-only table is:

| Type | Answerable questions | Recall@3 | Recall@5 |
| --- | ---: | ---: | ---: |
| ordinary | 9 | 1.0 | 1.0 |
| version_sensitive | 2 | 0.5 | 0.5 |
| exact_term | 4 | 1.0 | 1.0 |
| must_abstain | 2 | N/A | N/A |
| prompt_injection | 1 | 1.0 | 1.0 |

Version-sensitive recall is worst (one of two references missed), not exact-term
recall. Exact-term recall is 1.0 in this run; do not repeat the generic claim that
it must be lower. Dense vectors capture related course-registration language
but do not guarantee top-k recovery of the exact current clause after excluding
the old edition. The filter protects freshness, not completeness. Clause-number
lexical/BM25 fusion could improve this; it is a proposed next step, not an
implemented hybrid retriever. A two-question category has high variance.

The metric implementation is `eval/run_eval.py:53`. It uses
source plus normalized clause/heading references, deduplicates relevance pairs,
and excludes must-abstain questions from recall. Full answer/citation/abstention
results are in eval/results.json; all chunk/cache measurements are in
 eval/experiments.json. Citation membership is not full semantic entailment and
expected-text matching is diagnostic only. CI gates are in
`eval/run_eval.py:120`. The fictional CI set has its own baseline;
never compare it against the full public-corpus baseline.

## 6. Changing EMBED_MODEL on the API only

`api/app/retrieval/chroma.py:45` compares configured model,
dimension and backend with collection metadata and logs both sides. A deliberately
changed pin gave readiness/query 503 and health 200 with request_id=failure-C-demo;
metadata was restored afterward. Same dimension alone is insufficient because
different models define different vector spaces. Fix configuration and reindex;
restarting query replicas does not transform old vectors. Cache keys include the
index revision and model settings, and the indexer clears its namespace before
and after writes. Readiness also rejects partial building-state indexes.

## 7. A real failure and the hour-long qualification

No verified incident lasting more than an hour was recorded during this work.
Claiming an hour would invent evidence. The concrete integration failure was
Chroma 1.0.12 rejecting hnsw:space in modify() even when unchanged. Initial
indexing failed at collection metadata updates; testing against mocks alone had
missed the library restriction. The fix creates cosine configuration once and
omits immutable HNSW keys from later metadata updates:
`indexer/pipeline/store.py:47`. A live scaled-vector query
then returned cosine distance 0.0, and the regression double now rejects that
immutable key. Other real diagnoses were off-page PDF characters, detached OCR
clauses and retained page caches. Durations are not fabricated. If the students
have an actual hour-long incident from their own work, append its real timeline
and evidence during human review.


Final full evaluation confirms recall@3/5=0.9375, 28/28 valid citations and 2/2
correct absent-topic refusals. Fifteen of sixteen answerable questions returned
supported answers. q11 is the retained current-version retrieval miss. The
multipart obligation safeguard in `api/app/services/grounding.py:8` quotes actual
retrieved source/page clauses rather than strengthening should into must. These
are local real-model results, not a claim of cluster deployment.
