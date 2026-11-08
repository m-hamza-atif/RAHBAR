# Engineering notes

These notes distinguish local real-model behavior from the fixture-cluster
evidence. The deployment answers at the end supply the applied Kubernetes details.
The independent full public-corpus Kubernetes run is recorded in
`docs/evidence/public-corpus-kubernetes-runtime.json` and `eval/results.json`.

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
are supplied in the deployment details below.

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
The deployment answers below give the actual matching probe values and references.

## 3. CPU HPA and the 8% paradox

A CPU-utilization target is relative to requested CPU, not a direct measurement
of users waiting for an external LLM. Three replicas at 8% against a 70% target
would suggest ceil(3*8/70)=1 replica before the minimum-three constraint. An
I/O-bound API can have high latency while consuming little CPU. Request/generation
latency and cache metrics live in `api/app/routes/metrics.py:28`.
A stronger autoscaling design would expose in-flight generation or queue depth
through a Prometheus adapter/KEDA and bound concurrency. That custom scaling
signal is a recommendation, not an already deployed component. Cluster HPA
readings and manifest line references are supplied in the deployment answers and
`docs/evidence/endpoints-hpa.txt`.

## 4. Memory, limits, margin and exit 137

Real local GNU time measurements for full-corpus WSL indexing with OCR and stub
vectors: peak RSS fell from 1,083,120 KiB to 165,492 KiB (161.6 MiB) after
`indexer/pipeline/extract.py:153` explicitly released
retained PDF layouts. Both runs exited zero. Ollama is external and its memory is
not included. These are not Kubernetes pod peaks. Partner B separately reports
76.93 MB (73.36 MiB) during active fixture indexing, against a 1536 MiB container
limit, in `docs/evidence/kubectl-top.txt`. The recorded fixture margin is 1462.64
MiB. The committed evidence summarizes runtime sampling; it does not include the
raw sampling trace. The independent full-corpus run additionally sampled 232 MiB
working set and a kernel high-water value of 258,969,600 bytes (246.97 MiB) during
active indexing, against a 1536 MiB limit. The Job completed without an OOM kill.
That live high-water read is not a certified final peak after completion.

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


The original Phase 4 local evaluation recorded recall@3/5=0.9375, 28/28 valid citations and 2/2
correct absent-topic refusals. Fifteen of sixteen answerable questions returned
supported answers. q11 is the retained current-version retrieval miss. The
multipart obligation safeguard in `api/app/services/grounding.py:8` quotes actual
retrieved source/page clauses rather than strengthening should into must. These
were local real-model results. The independent full Kubernetes evaluation now
records the same recall and abstention correctness, with 29/29 valid citations;
its per-question answers are in `eval/results.json`.

## Deployed Kubernetes settings

**Q1 — single writer.** Three readers are set at `k8s/base/api.yaml:7`. The Job
retry budget is `k8s/base/indexer.yaml:7`, weekly Forbid at
`k8s/base/reindex.yaml:9`. `scripts/deploy.py:50` suspends the schedule and rejects
unfinished Jobs before manual indexing; `indexer/entrypoint.py:15` obtains a
renewable Redis lease against a manual/scheduler race. This avoids duplicate
startup writers, repeated OCR on restarts, the readiness dependency trap, and
unnecessary query deployments for a corpus refresh. During in-place writes,
Partner A's index_state/revision checks deliberately make readers unready.

**Q2 — 90-second Chroma stall.** Actual liveness is `/healthz` with period 20s and
failureThreshold 3 (`k8s/base/api.yaml:70`); readiness is `/readyz`, period 10s,
failureThreshold 3 (line 77). Startup is `/healthz`, period 2s, threshold 30
(line 63). If swapped, dependency failures can trigger correlated restarts after
roughly 40–60 seconds plus probe timeouts, while the readiness endpoint reports
the process alive and admits broken readers. Exact restart counts cannot be
computed as 90/20: startup, timeout, termination and backoff matter. The 90-second
case is analysis, not an invented timed experiment. The isolated wrong-pin live
test verifies health 200/readiness 503 and removes the failing replica afterward.

**Q3 — CPU HPA underestimates generation.** The 70% target is at
`k8s/base/hpa.yaml:19`, with requested API CPU at `k8s/base/api.yaml:47`.
At 8% CPU, ceil(3*8/70)=1 before minReplicas=3 clamps it. Waiting for Ollama can
inflate latency without CPU load. A measured in-flight generation gauge could
be exposed through Prometheus Adapter as a Pods metric; an actual queue could
instead feed KEDA. Both require bounded worker concurrency and a max compatible
with the model host's capacity. Neither adapter nor queue is falsely claimed as
implemented. Metrics-server/HPA runtime evidence is recorded separately.

**Q4 — memory and exit 137.** Configured API request/limit is 128/512 MiB
(`k8s/base/api.yaml:48`); indexer is 512/1536 MiB
(`k8s/base/indexer.yaml:41`). Chroma is 256/1024 MiB, Redis 64/256 MiB and UI
32/64 MiB. These are bounded initial budgets.
Measured fixture indexer peak memory is 76.93 MB (~73.36 MiB) at 108.68% CPU, captured via container runtime sampling during an active reindex run (`docs/evidence/kubectl-top.txt`). With the configured 1536 MiB limit, the fixture safety margin is 1536 MiB - 73.36 MiB = 1462.64 MiB (95.2% headroom). The Job exited 0 with no OOMKilled events.
For full-corpus indexing with OCR, Partner A's measured WSL process peak RSS was
165,492 KiB (~161.6 MiB) after releasing PDF layouts
(`indexer/pipeline/extract.py:153`). That process measurement is not a container
measurement and cannot establish the full-corpus Kubernetes safety margin.
The independent full Kubernetes run observed 232 MiB working set with
`kubectl top` and a cgroup memory.peak counter of 246.97 MiB while the indexer
was active. Headroom against that observed high-water sample was 1289.03 MiB;
the final post-completion peak was not certified. The Job processed all 875
chunks/37 OCR pages and exited successfully. The sample and applied limit are
recorded in `docs/evidence/public-corpus-kubernetes-runtime.json`.
Exit 137 is SIGKILL (128+9); check OOMKilled status, events and previous logs before
attributing it to memory. Margin must be calculated as configured limit minus measured peak from the same run, not guessed.
