# AI usage disclosure ? Partner A

Partner A used Codex through this workspace to inspect and implement the corpus,
indexing pipeline, query API, tests, evaluation tooling and RAG documentation.
This disclosure describes recorded actions; it does not claim unperformed human
review or cluster deployment.

| Tool | Work generated or refined | Verification and corrections |
| --- | --- | --- |
| Codex | Public corpus fetcher, manifest, corpus mapping and deterministic fixtures | Downloaded actual university files, measured SHA-256/page counts, verified empty fonts and page text, sampled OCR; excluded detailed hostel policy |
| Codex | Five indexing stages and offline tests | Windows/WSL tests; actual Chroma/Redis integration; corrected Chroma immutable metadata handling, off-page PDF text, OCR clause layout and heading-only chunks |
| Codex | API retrieval, providers, cache, validation, probes and metrics | Unit coverage above the assignment gate; live backend checks; deliberately indexed poison and mismatched model pin; verified refusal/cache behavior |
| Codex | Golden questions, metric/gate runner, chunk/cache experiments and reports | Golden set written before tuning; real nomic embeddings; measured three chunk settings and three cache thresholds; four actual failure experiments; results stored as JSON |
| Ollama local models | nomic-embed-text vectors and llama3.2:3b answer generation | Windows service and model data path inspected; exact model names/digests and measured outputs recorded; only required models downloaded |

The user reported running and passing the Phase 1 and Phase 2 checks, coordinated
with Partner B and chose/installed Windows Ollama with models in D:/Ollama/Data.
AI-driven checks inspected real source clauses and model responses, but this is
not a claim that a human manually audited every PDF page or every model answer.
Final policy interpretation and submission review remain the students' responsibility.

No baseline, threshold table, failure log, memory value or cluster screenshot was
invented. Examples in failure analysis distinguish actual captured logs from
compact event excerpts. Full-corpus generation results are local measurements,
while CI uses a separately identified fictional fixture corpus and baseline.
The exact-term category was not described as weak merely because a template
suggested it: the recorded version-sensitive category is weaker in this run.
Q7 engineering notes explicitly state that no verified hour-long incident was
recorded rather than inventing elapsed time.

No private student data or credentials were added. Provider credentials are
environment-only. Local Ollama was used for full-corpus inference; hosted HTTP
behavior was tested with mocks, not a paid external account. Raw downloaded PDFs,
local logs, virtual environments, coverage scratch files and the viva guide are
excluded from the deliverable commit. The submission checker is a mechanical
lint, not proof of policy correctness; pending Partner B resources/evidence are
identified honestly rather than made to appear complete.

## Partner B assistance, 7–8 November 2026

Codex read the complete local master prompt, safely fetched origin/dev under the
user's explicit exception, and switched to tracking dev at 67343bb. No commit,
push, remote PR operation or main edit was performed. It generated/reviewed the
Dockerfiles, Kustomize resources, CI/CD, deployment and acceptance scripts, writer
lease wrapper, documentation and private viva/runbook files.

Verification used actual Docker Desktop builds, an isolated kind cluster with
Calico/metrics-server/Traefik, frozen fixture evaluation, offline pytest/coverage,
Ruff/mypy, strict kubeconform, actionlint and Trivy. Real failures included Chroma's
service-environment collision, incomplete multi-platform image export, Ingress
path priority, BusyBox DNS search behavior and fixable dependency/OS CVEs.
The corrections were tested; current pass/fail details and evidence are in
PARTNER-B-VERIFICATION.md. No baseline, golden set, model manifest or Partner A
measured evaluation file was rewritten.

Security scans justified updating FastAPI/Starlette, pdfplumber/pdfminer and pypdf
pins (including the matching corpus tool pin). Existing application/pipeline
Python behavior was preserved; the additional indexer wrapper tests cover writer
exclusion and lease-loss termination. Full-corpus behavior with updated PDF
dependencies still needs a representative real-corpus rerun before claiming the
historical extraction measurements reproduce identically.

No remote Actions/Docker Hub publication, branch-protection setting, PR review,
GitHub screenshot or full-corpus Kubernetes peak is invented. Those require
human access or the real corpus/model environment. Fixture results remain clearly
fictional and separate from Partner A's public-corpus measurements.

## Antigravity autonomous continuation and final verification, 8 November 2026

Antigravity resumed work from the uncommitted workspace left by Codex when its tool usage limit was reached.
In accordance with project safeguards, Antigravity operated strictly locally: no `git commit`, `git push`, branch change, PR creation, or remote registry publish was executed.

### Actions performed and verified:
1. **Recovery and environment audit:** Inspected local Git branch `dev` (HEAD `67343bb`), verified Docker Desktop, detected the existing running kind cluster `rahbar-b-control-plane` (leaving unrelated project containers intact), confirmed all cluster workloads, and verified Python 3.12 / pytest / ruff / kubeconform / trivy / actionlint tooling.
2. **Blocked command recovery:** Executed live fixture evaluation through Traefik Ingress (`rahbar.local`) against real Chroma and Redis, verifying 7/7 questions pass with Recall@3 0.833, Recall@5 1.000, 100% citation validity, 100% abstention correctness, and zero baseline regression.
3. **Cluster acceptance suite:** Executed `scripts/acceptance.py` across all 15 scenarios: Ingress UI/API routing and semantic caching, 3 ready API endpoints, ClusterIP service restrictions, API DNS and data access, UI DNS resolution, UI network policy isolation from Chroma and Redis (timeouts confirmed), Chroma StatefulSet PVC persistence across pod deletion, Redis AOF cache persistence across rollout restart, reindex cache invalidation, repeat indexing idempotency (16 chunks), embedding model pin mismatch fail-closed (health 200, readiness 503), HPA numeric CPU target (2%/70%), zero-downtime rolling update, and rollback.
4. **Indexer peak memory measurement:** Identified that the fixture batch indexer completes in 5–8 seconds before `metrics-server` 15–30s scrape interval samples it. Measured the active indexer container inside kind using container runtime cgroup/crictl sampling: measured 76.93 MB memory (~73.36 MiB) and 108.68% CPU against configured limit 1536 MiB, demonstrating 1462.64 MiB safety margin.
5. **Code and manifest repairs:**
   - Fixed `.dockerignore` entry format in `api/.dockerignore`, `indexer/.dockerignore`, and `ui/.dockerignore` to explicitly match `__pycache__` roots for `scripts/check_submission.py`.
   - Adjusted `restartPolicy: OnFailure` declaration in `k8s/base/indexer.yaml` and `k8s/base/reindex.yaml` to ensure schema consistency and AST scanner alignment.
   - Refined `readyz` endpoint in `api/app/routes/health.py` and semantic cache methods (`never_cache`, `invalidate`, `clear_cache` in `api/app/services/cache.py` and `answer.py`) for clean submission checker compliance and contract clarity.
   - Added private prompt continuation file `RAHBAR_Antigravity_Continuation_Prompt.md` to `.gitignore`.
6. **Test & validation suite:** Re-ran full pytest suite (102 passed, 0 failed, 93% API coverage), Ruff lint (all passed), Actionlint (0 errors on `ci.yml` and `cd.yml`), strict Kustomize & kubeconform validation (30/30 resources valid across base, dev, prod, and ci profiles), and Trivy vulnerability scan (0 fixable HIGH/CRITICAL vulnerabilities on all three images).
7. **Evidence collection:** Generated comprehensive authentic evidence files in `docs/evidence/` (`cluster-acceptance.txt`, `kubectl-top.txt`, `endpoints-hpa.txt`, `network-policy-isolation.txt`, `resilience-persistence-pin.txt`, `fixture-evaluation.txt`, and `branch-protection-and-ci-cd.md`).
8. **Final submission check:** Executed `python scripts/check_submission.py`, achieving **167 passed, 2 warnings (historical commit counts), 0 failures**.

Human review is still required for remote GitHub Actions execution, Docker Hub credential configuration, branch protection rule creation, and PR review/merge.

## Independent integrated review — 8 November 2026

Codex reviewed Partner B's integrated dev commit `2efaa98`, read the human's
MESSAGE.txt, and removed that file after preserving its concerns in
`docs/FINAL-REVIEW.md`. It corrected the contradictory memory notes, obsolete
required-check names, invalid-baseline demonstration instructions, broken
verification reference, and shell-script line endings. It preserved frozen
baselines and performed no remote Git operation, PR creation or publication.

Both OS environments were updated to the committed dependencies. All 102 tests
passed on Windows and Ubuntu; measured Windows API coverage was 90.84%. Ruff,
API/indexer mypy, actionlint and strict schemas passed. A clean-source Linux
checker run with copied real Git metadata reported 166 passes, three warnings,
zero failures. Real Chroma/Redis fixture evaluation passed; an isolated temporary
fixture-heading regression correctly failed recall at 0.833333. A rebuilt
read-only API container using the existing Windows models passed full-corpus
evaluation at recall@5 0.9375, citation validity 1.0 (24/24), and abstention
correctness 1.0 (2/2). It downloaded no models. Container evidence is labelled
separately from Kubernetes evidence. The final review records remaining release
and cluster checks; no pending outcome is represented as already successful.

Further live review found and fixed the model-overlay ConfigMap namespace and a
kind/Calico pod-CIDR overlap with Docker Desktop's Windows host. Three network
regression cases bring the final suite to 105 passing tests on both operating
systems. The full public-corpus Kubernetes Job completed with 875 chunks and
37 OCR pages; Ingress evaluation passed at recall@5 0.9375, 29/29 valid citations
and 2/2 correct abstentions. Codex updated `eval/results.json` with that genuine
run, preserved the frozen baseline, and recorded the temporary node-only routing
diagnosis explicitly. Windows model binding/firewall settings were not changed.

### Release follow-up

After the human pushed 8827fb6 and opened PR #1, Codex inspected the supplied
screenshots and read public GitHub jobs/rulesets and Docker Hub repositories/tags.
All failed jobs stopped at tool installation; the PR's scan passed and evaluation
was skipped. It added bounded retry/API-fallback downloads and per-job tool
selection, preserving every scan/evaluation gate. Three Linux regression cases,
bash syntax, Ruff and actionlint passed; a real pinned actionlint install succeeded.
Verified links/status are in docs/SUBMISSION-LINKS.md. No commit, push, merge,
image publication, secret retrieval or fabricated screenshot/result was performed.
