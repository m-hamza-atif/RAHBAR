# Evaluation, tuning and reproduction

## Two intentionally separate profiles

| Profile | Documents/model | Golden set | Baseline | Relevance floor |
| --- | --- | --- | --- | ---: |
| Public corpus | 8 public documents, nomic-embed-text/768 plus llama3.2:3b | eval/golden.yaml | eval/baseline.json | 0.35 |
| CI fixtures | fictional Markdown, deterministic hash/384 plus stub generation | eval/fixtures/golden.fixture.yaml | eval/fixtures/baseline.fixture.json | 0.15 |

The full set contains 18 questions: nine ordinary, two version-sensitive, four
exact-term, two must-abstain and one injection. It was written before tuning.
The fixture set contains seven questions, including an explicit 2023 probe.
Raw public PDFs and model weights are not committed. Model names/digests/sizes
are in eval/model-manifest.json. The two required models occupy about 2.3 GB
in the user's configured D:/Ollama/Data; no additional variants are required.

## Full measured results

Real-generation recall@3=0.9375, recall@5=0.9375, citation validity=1.0,
and must-abstain correctness=1.0. The answered-from-context flag rate
on answerable questions is 0.9375. Exact per-question outputs, expected-text
diagnostics, durations and by-type metrics are in eval/results.json. The baseline
is a compact snapshot of aggregate/by-type metrics plus provenance, not a second
copy of every answer. This is a small in-sample tuning set, not held-out evidence
of general accuracy. Citation validity is membership in retrieved references,
not a semantic entailment judgement. Read the actual answers before claiming quality.

The runner computes recall using source plus normalized clause/heading. It does
not conflate different source filenames. A clause label such as Clause 1.21
matches 1.21 followed by descriptive text; non-clause headings retain their full
normalized title. Duplicate expected references are counted once. Must-abstain
questions have no applicable recall and are excluded from recall means. Citation
validity is weighted per citation and checks exact source, section and page.
When no citations exist the aggregate validity is vacuously 1; the separate
answered flag and retrieval metrics make that limitation visible.

## Reproduce the public-corpus indexing experiments

The user's Windows tray Ollama is bound to loopback. WSL OCR tools are installed,
but a second Ollama server or a broad network binding was not needed. From the
repository root in Ubuntu, prepare the extraction cache:

```bash
.venv-wsl/bin/python eval/run_experiments.py --extract-only
```

Then from PowerShell in the same repository, with Docker Desktop and Windows
Ollama running and the two models already installed:

```powershell
uv run --no-project python eval/run_experiments.py
```

This runs 256/32, 512/64 and 1024/128 structure settings plus fixed 100/0 using
real embeddings, records model/input/golden hashes, measures cache pairs and
OCR/version failures, installs the selected production collection rahbar_policies,
and removes temporary tuning collections/vector cache. Input cache and extraction
logs remain ignored under corpus/raw. The API must not index at startup.
Adding --api http://127.0.0.1:8000 also runs/restores the model-pin failure against
an already running API. Keep all indexing runs single-writer and do not do this
during an active evaluation run. Windows and WSL checks use separate virtualenvs.

Start the real API from PowerShell:

```powershell
$env:RETRIEVER='chroma'
$env:LLM_PROVIDER='ollama-host'
$env:EMBED_MODEL='nomic-embed-text'
$env:EMBED_DIM='768'
$env:LLM_MODEL='llama3.2:3b'
$env:OLLAMA_BASE_URL='http://localhost:11434'
$env:CHROMA_HOST='localhost:8001'
$env:CHROMA_COLLECTION='rahbar_policies'
$env:RELEVANCE_FLOOR='0.35'
$env:CACHE_THRESHOLD='0.90'
$env:REDIS_FAKE='false'
uv run --no-project uvicorn app.main:app --app-dir api --host 127.0.0.1 --port 8000
```

In another terminal, evaluate without changing the committed baseline:

```powershell
uv run --no-project python eval/run_eval.py --api http://127.0.0.1:8000
```

Only after an intentional improvement, use --update-baseline. Failed gates cannot
overwrite the baseline. X-Cache-Bypass=true is sent by default so each query tests
actual retrieval/generation. --use-cache opts into cache-inclusive testing.
A 300-second request deadline permits initial model loading and one bounded retry.
The golden hash prevents accidentally comparing different question sets. It hashes
UTF-8 text with normalized LF line endings, so Windows CRLF and Linux LF checkouts
produce the same dataset identity. Corpus PDF checksums still hash exact bytes.

## Fast CI reproduction

No model download or GPU is needed. Build/package eval/fixtures at /fixtures and
set both API and indexer to EMBED_MODEL=stub and LLM_PROVIDER=stub. Use
RETRIEVER=chroma, EMBED_DIM=384, TOP_K=5, RELEVANCE_FLOOR=0.15 and matching
collection/service addresses. Redis must be real/reachable in integration CI;
REDIS_FAKE=true is reserved for unit tests. Wait for dependencies, complete the
indexer Job, then wait for API readiness and run:

```bash
python eval/run_eval.py --api http://YOUR_API --golden eval/fixtures/golden.fixture.yaml --baseline eval/fixtures/baseline.fixture.json --out /tmp/results.fixture.json
```

The measured fixture baseline has recall@3/5=1.0, citation validity=1.0 and
abstention correctness=1.0. The floor was measured at 0.15/0.25/0.35, rather
than using a trained-model threshold with hash vectors. To reproduce that local
calibration against Docker services on 8001/6379, run:

```bash
python eval/calibrate_fixtures.py
```

--update-baseline is optional and explicit. This helper creates only a local
fixture collection, uses the actual API route with real Chroma/Redis and does
not download models. It never substitutes fixture results for the full corpus.

## Gate and interpretation

Exit 1 means recall@5 fell more than five percentage points below the correct
baseline, citation validity fell below 0.95, abstention correctness fell below
1.0, the baseline/dataset was wrong, or required metrics were missing/invalid.
A transport error also fails the command; it is not a passing empty result.
The initial baseline needs an explicit --update-baseline. Neither thresholds nor
gates were weakened to hide failures. Metric/gate unit tests cover exact boundary
values, undefined recall, page mismatch and refusal to overwrite on a failed run.

Chunk/cache measurements and failure evidence are in eval/experiments.json and
docs/FAILURE-ANALYSIS.md. Local PDF-process memory is measured separately from
Ollama and from Kubernetes. Cluster CPU/memory, rollout/HPA and screenshot evidence
must still come from Partner B's actual deployed manifests. Those results cannot
be inferred from local tests or generated by this report.


Final AI-assisted spot review retained the one version-sensitive retrieval miss
(q11) instead of rewriting the golden question to raise the score. Some yes/no
answers remain terse (for example a Boolean-looking answer string), which is why
expected-substring mismatches are diagnostic rather than automatic semantic failures.
The multipart Clause 4.4 answer is now verbatim evidence preserving must/should
and the second-warning condition. Review notes are in eval/generation-review.json.
