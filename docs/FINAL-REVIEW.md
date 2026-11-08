# Independent final review — 8 November 2026

Release follow-up: the human has since pushed `8827fb6`, opened PR #1 and added
Docker Hub secrets. See [current submission links/status](SUBMISSION-LINKS.md)
for the subsequent download failures, fixes and remaining steps. The original
review below predates that PR.

Reviewed integrated `dev` at `2efaa98` and the local fixes listed below. The code
checks pass; the submission still needs the real GitHub release and its URLs.
No remote Git operation, PR, image publication or merge was performed by this review.

## Four submission items

| Item | Verified status | Remaining action |
| --- | --- | --- |
| GitHub repository URL | `https://github.com/m-hamza-atif/RAHBAR` is public | Push the reviewed local changes manually |
| Successful `cd.yml` run that tested, published and deployed | Not yet verified | Configure Docker Hub secrets; approve and merge the real PR into main; wait for all three CD jobs to succeed; copy that run URL |
| Docker Hub image links with SHA tags | Publication not yet verified | After CD succeeds, verify all three repositories contain the exact merged commit SHA and copy their URLs |
| `eval/results.json` and `eval/baseline.json` committed | Both are tracked; results updated locally with the final real Kubernetes run | Commit the updated results with the fixes; the frozen baseline is unchanged |

The full-corpus committed evaluation records recall@5 0.9375, citation validity
1.0 and abstention correctness 1.0. Its current-version retrieval miss remains
documented. These are local real-model results, not Kubernetes inference evidence.

## Independent checks

- Updated both existing Python environments to the committed Partner B dependency
  versions before final tests (including FastAPI 0.162.2, Starlette 1.3.1,
  pdfplumber 0.11.10 and pypdf 6.21.4).
- Windows and Ubuntu: 105 tests passed, including three network regression cases.
  Windows API coverage: 90.84%, above the
  required 60%. One dependency deprecation warning concerns TestClient's future
  httpx migration; it does not fail the tests.
- Ruff passed for API, indexer, evaluation, corpus and scripts; mypy passed for
  both API and indexer. Actionlint passed for both workflows.
- All four rendered Kubernetes profiles passed the manifest invariants and strict
  kubeconform schemas: 30 valid resources per profile, zero errors or skips.
- Real local Chroma 1.0.12 and Redis fixture integration passed: recall@5,
  citation validity and abstention correctness each 1.0. A temporary isolated
  section-heading regression reduced recall@5 to 0.833333 and correctly failed
  the recall gate. The source fixtures, golden files and baselines were preserved;
  the temporary review collection was removed.
- Corpus verification: all eight local source files match the committed manifest.
- Windows submission checker: 164 passed, four warnings, zero failures. Warnings
  include Windows traversal of the Linux environment, placeholder Secret history,
  commit count and author distribution; a checker pass is not a full rubric grade.
- Ubuntu checker against a clean copy of the working source files and real Git
  metadata: 166 passed, three warnings, zero failures. This avoids scanning local
  virtual environments and caches; the checker itself was not changed.
- A read-only API-image container reached the existing Windows Ollama service via
  `host.docker.internal` and confirmed the two required models. No model was added.
- All three fresh Docker image builds passed. Full public-corpus evaluation through
  the rebuilt read-only API container passed the frozen gate: recall@3/5 0.9375,
  24/24 valid citations, 2/2 correct abstentions, 15/16 answerable questions answered.
  Model digests matched `eval/model-manifest.json`. See
  [container evaluation](evidence/public-corpus-container-evaluation.json).
  Generation varies, so the citation count differs from the older 28-citation run;
  the frozen baseline remains intact. The latest Kubernetes run below now supplies
  `eval/results.json`; the original local run remains in Git history.
- The rebuilt indexer container also processed all eight public documents under
  a 1536 MiB/1.5 CPU limit and read-only root: 875 chunks, 37 OCR pages, exit 0,
  no OOM kill. The highest cgroup peak observed during OCR was 258,809,856 bytes;
  this is not presented as the final Kubernetes Job peak. See
  [indexer evidence](evidence/public-corpus-container-indexer.json).
- Full public-corpus Kubernetes deployment through Traefik Ingress passed the
  frozen evaluation gate: 875 indexed chunks, 37 OCR pages, three ready API
  endpoints, recall@5 0.9375, 29/29 valid citations, 2/2 correct abstentions and
  15/16 answerable questions answered. UI returned 200, Redis shared cache reuse
  succeeded, HPA reported numeric CPU, and UI egress to Redis/model host timed out
  under NetworkPolicy. The completed Job exited successfully. See
  [runtime evidence](evidence/public-corpus-kubernetes-runtime.json) and
  [latest evaluation](../eval/results.json).
- A separate fresh cluster created by the corrected helper assigned pods from
  `10.244.0.0/16` and reached Windows Ollama with HTTP 200 under default-deny and
  exact model egress. It needed no manually added model SNAT rule. See
  [fresh network proof](evidence/fresh-network-verification.json). This check
  verifies the network correction; the full RAG run is the earlier evidence above.

Runtime outputs from this review are in ignored `.artifacts/`. Partner B's earlier
fixture-cluster evidence remains in `docs/evidence/`; it must not be relabelled as
full-corpus evidence or as a new independent run.

## Corrections made

- Reconciled the early memory answer with Partner B's reported fixture measurement
  of 76.93 MB (73.36 MiB). Full-corpus Kubernetes memory remains unmeasured; a WSL
  process RSS cannot establish the container safety margin. The committed fixture
  evidence summarizes runtime sampling rather than including its raw trace.
- Corrected required GitHub check names to `lint`, `test`, `manifests`, `build`,
  `scan`, `e2e-eval`, matching the actual workflow.
- Replaced instructions to corrupt the frozen baseline with the verified isolated
  fixture-heading regression. Standardized the three screenshot paths.
- Replaced the README's broken verification link with this report.
- Added LF enforcement for shell scripts so the installer runs from a Windows
  checkout mounted in WSL; CRLF previously caused `pipefail` parsing to fail.
- Fixed `scripts/configure_model.py` to include the ConfigMap namespace. Both
  generated dev/prod overlays now render; all three tested local model overlays
  passed strict schema validation (93 resources total).
- Corrected the fresh kind pod subnet to `10.244.0.0/16` and seed the matching
  Calico pool before apply. The older `192.168.0.0/16` overlapped the Windows
  model host at `192.168.65.254`: a pod timed out despite correct egress policy.
  A destination/port-specific SNAT rule inside this review's existing disposable
  node restored access and confirmed the diagnosis. The Windows listener/firewall
  were not changed. Existing clusters are not silently migrated. A fresh CI run
  after the human pushes these changes must verify the final combined diff.

## Remaining release and evidence steps

1. Review and manually commit/push these fixes to `dev`. Wait for fresh green CI.
   The public CI page already shows success at `2efaa98`; this predates these fixes.
2. In GitHub Settings, configure `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`, and
   protect main with the actual six required checks and one approval.
3. Follow `docs/evidence/branch-protection-and-ci-cd.md` for a genuine failed-gate
   PR, its correction and green checks. Capture `branch-protection.png`,
   `blocked-merge.png`, and `green-checks.png`; none existed in the reviewed checkout.
   These support the rubric even though the Classroom list asks for four items.
4. Open/approve/merge the real release PR to main manually. Record the successful
   CD run and the three SHA-tagged Docker Hub image URLs. Do not call a local
   workflow review or green CI a successful CD deployment.
5. Full public-corpus Kubernetes inference is now verified separately from CI
   fixtures. Preserve that distinction in the submission: CD deploys the fixture
   profile; `eval/results.json` records the real public-corpus Kubernetes run.

The public PR page showed zero open and zero closed PRs during this review. No
successful CD run was verified. No screenshot or remote result was fabricated.

Public sources: [CI runs](https://github.com/m-hamza-atif/RAHBAR/actions/workflows/ci.yml),
[pull requests](https://github.com/m-hamza-atif/RAHBAR/pulls).

Temporary review clusters/containers, duplicate review collections and image
transfer archives are removed after recording evidence. The original local
Chroma/Redis containers and their production/fixture collections are preserved.
The two existing Ollama models are unloaded from memory; weights and the Windows
application remain installed. Private `CODEX_REQUESTS.md` gives the exact manual
commit/push, Docker Hub setup and release steps.
