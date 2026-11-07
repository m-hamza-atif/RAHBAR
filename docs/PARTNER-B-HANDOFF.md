# Consolidated Partner A handoff after Phases 3-4

For Partner B's coding agent: inspect the pulled files first. This works from a
fresh start or alongside existing work. Preserve both partners' changes. Implement
the integration yourself; give the human only actions requiring their access.
Reference results below are observations to reproduce, not values to hardcode.

## Starting state and manual Git ownership

Partner B is starting from scratch with Partner A's completed work available.
The human will pull the latest dev before starting the agent. Verify the checkout
and preserve existing files; do not assume historical starter code is current.
If required code is missing, ask the human to synchronize it while continuing
independent work. Do not restart Partner A's completed phases.

Humans handle fetch/pull/push and branch integration. The agent must not execute
those operations, rebase/reset/force-push, or merge remote PRs. Inspect Git read-only,
prepare reviewable changes, and provide the human exact safe commands. Create local
commits only when requested. Sharing dev is acceptable; a separate feature branch
is optional. Implementing publishing workflows remains in scope, but actual
external publication requires human authorization/source pushes.

## What is now available

The corpus/indexer, production API path, Redis cache, real probes, metrics,
evaluation runner, full/fixture baselines and experiments are implemented.
Read docs/API.md, docs/EVALUATION.md and docs/PIPELINE.md. The API still starts
with uvicorn app.main:app from api/; the indexer still starts with
python -m pipeline.run from the directory containing pipeline/. No route or port
changes are required. Root Makefile test/eval-fixtures targets were updated;
preserve those changes when reconciling your image-build commands.

## CI profile: no Ollama or downloaded PDFs

Package eval/fixtures inside the indexer image at /fixtures. Use a root build
context or prepared isolated context and keep all Makefile/workflow build calls
consistent with that choice. Install the updated indexer/requirements.txt plus
tesseract-ocr/poppler-utils; install api/requirements-dev.txt for pytest-cov in CI.
The root pytest configuration now includes evaluation and corpus unit tests.

Use these matching API/indexer settings where applicable:

| Variable | CI value |
| --- | --- |
| RETRIEVER | chroma |
| LLM_PROVIDER | stub |
| EMBED_MODEL | stub |
| EMBED_DIM | 384 |
| CHROMA_COLLECTION | rahbar_policies, or another name shared by both workloads |
| CHROMA_HOST / CHROMA_PORT | your Chroma Service / 8000 |
| REDIS_HOST / REDIS_PORT | your Redis Service / 6379 |
| REDIS_FAKE | false |
| CORPUS_DIR | /fixtures (indexer only) |
| CHUNK_SIZE / CHUNK_OVERLAP | 512 / 64 |
| TOP_K | 5 |
| RELEVANCE_FLOOR | 0.15 (measured hash-fixture setting) |
| CACHE_THRESHOLD | 0.90 |

Keep client/server Chroma at 1.0.12 unless a coordinated, tested update changes
both. Start/wait for Chroma and Redis, complete the indexer Job, then wait for
API readiness. Do not require a hosted LLM API key for stub or local Ollama modes;
omit the Secret reference in CI or make it optional rather than leaving pods
blocked on an unnecessary missing Secret. Never commit credentials.

Run the actual CI gate against the fixture baseline:

```bash
python eval/run_eval.py --api http://API_ADDRESS --golden eval/fixtures/golden.fixture.yaml --baseline eval/fixtures/baseline.fixture.json --out /tmp/results.fixture.json
```

For an Ingress host rule, add --host rahbar.local. The seven-question measured
fixture baseline has recall@3/5=1.0, citation validity=1.0, abstention correctness=1.0.
Do not use eval/baseline.json for this fixture job. Cache is bypassed by default
so the gate actually tests retrieval/generation. A failed run must stay failed;
do not update baselines or weaken gates automatically in CI.

## Real-model profile and storage

Production/local real-model values are nomic-embed-text, EMBED_DIM=768,
LLM_PROVIDER=ollama-host, LLM_MODEL=llama3.2:3b, TOP_K=5,
RELEVANCE_FLOOR=0.35, CACHE_THRESHOLD=0.90 and chunking 512/64.
Both model manifests/digests are recorded in eval/model-manifest.json. Supply
the real downloaded corpus plus _index.json separately; PDFs are not in Git.
Set CORPUS_DIR to the actual mounted/fetched path. Production evaluation uses
eval/golden.yaml and eval/baseline.json. Do not download models/full corpus in
fast CI. Do not bake Windows model directories into Docker images.

Ollama is installed on Partner A's Windows machine and data stays in D:/Ollama/Data.
The local experiments used Windows inference plus a WSL OCR extraction cache,
because the loopback tray server was not reachable from WSL. Neither WSL nor
minikube should be assumed to reach that server by default. Configure and verify
trusted host/cluster connectivity only when doing the real deployment; stub CI
is independent. OLLAMA_BASE_URL is preferred, with OLLAMA_URL retained as an alias.

Partner A's Windows installation is a reference environment, not an endpoint
automatically available on Partner B's different computer. Finish stub CI without
it. For a required real-model deployment, agree with the human on an actually
reachable model host; do not assume your localhost is Partner A's machine or
download models merely to run CI.

The indexer marks building/ready and invalidates only rahbar:cache:*; the API
checks state, revision, model, dimension, backend, count and Redis. Do not put
indexing in API startup. CronJob concurrencyPolicy=Forbid does not prevent a
separate manual Job; coordinate manual and scheduled writers. Rebuilds use a
readiness maintenance window, not an atomic blue/green swap.

## Remaining Partner B work and honest evidence

Create/review Dockerfiles, manifests, NetworkPolicies, probes, PVCs, HPA and
workflows, then run image/manifest/cluster checks yourself. Capture real pod
resources, endpoints, HPA, rollout and branch-protection/evaluation-gate evidence.
Local PDF-process RSS was reduced to about 162 MiB; this is not a cluster peak
or a substitute for kubectl top pods under the actual image/limit. Update Q1-4
of docs/ENGINEERING-NOTES.md with deployed manifest line numbers and measurements,
preserving Partner A's Q5-7. Reconcile ADRs rather than overwriting either track.

The root README is still Partner B's clean-clone/architecture/deployment guide.
The overall submission checker cannot be called clean until your artifacts and
evidence are merged. Never fabricate screenshots, resource readings or successful
CI publication. Partner A's local virtual environments and model files are not
submission artifacts and should not be copied into images.

Partner B's agent owns the first combined-system integration: reconcile interfaces,
build/test the deployed fixture stack against its correct baseline, fix concrete
compatibility problems, complete documentation/evidence and report genuine
remaining blockers. Then provide manual Git instructions to the human. After the
human pushes the finished work to dev, Partner A will pull manually and request
an independent final Codex review. That second review does not replace Partner B's
own complete integration checks.

Final reference counts are 875 real-model chunks and 16 current CI fixture chunks.
The final offline suite has 99 tests and API coverage about 92.96%. The root README
and cluster files are intentionally still yours; this checkout has not received
your branch, so its whole-project submission lint still reports those missing artifacts.
