# Indexing pipeline — Phase 2

The indexer is a one-shot writer. Run `python -m pipeline.run` from `indexer/`,
or set `PYTHONPATH=indexer` from the repository root. The API does no indexing.
The existing `--dummy` entrypoint remains available and uses the same storage
and cache-invalidation path, pinned as `dummy-768` with 768 dimensions.

## Configuration and local execution

Settings are read only from environment variables. Defaults are:

| Setting | Default / meaning |
| --- | --- |
| CHROMA_HOST / CHROMA_PORT | localhost / 8000; host:port also accepted |
| CHROMA_COLLECTION | rahbar_policies |
| CORPUS_DIR | repository corpus/raw, independent of working directory |
| CHUNK_SIZE / CHUNK_OVERLAP | 512 / 64 whitespace tokens |
| CHUNK_STRATEGY | structure; fixed available for controlled comparisons |
| ENABLE_OCR | true; false logs missing-text risk for the extraction experiment |
| EMBED_MODEL | nomic-embed-text |
| LLM_PROVIDER | ollama-host; stub selects deterministic offline embeddings |
| OLLAMA_BASE_URL | host.minikube.internal:11434 over HTTP; OLLAMA_URL remains an alias |
| EMBED_BATCH_SIZE | 32 |
| REDIS_HOST / REDIS_PORT | localhost / 6379 |
| REDIS_URL | optional complete connection URL overriding host/port |
| CHROMA_PERSIST_DIR | optional; requires full chromadb rather than the HTTP-only client |

The default Ollama URL falls back to localhost on connection failure. No server
installation or model download occurs automatically. A bad HTTP/model response
fails the job. All logs, including Python library warnings, are JSON on stdout.

From Ubuntu WSL, with the uv-managed .venv-wsl created during setup:

```bash
cd '/mnt/d/University/SCD/Assignment 2/rahber-starter'
export PYTHONPATH=indexer
export CHROMA_HOST=localhost CHROMA_PORT=8001
export REDIS_HOST=localhost REDIS_PORT=6379
export EMBED_MODEL=stub LLM_PROVIDER=stub
export CORPUS_DIR="$PWD/eval/fixtures"
export CHROMA_COLLECTION=rahbar_phase2_fixtures
.venv-wsl/bin/python -m pipeline.run
```

Use a separate collection for fixtures and the full corpus. Stub embeddings are
for deterministic tests, not a measurement of production semantic quality.
Use `EMBED_MODEL=stub` explicitly for these runs. If LLM_PROVIDER=stub is used
with another configured model name, metadata still records the configured name
and additionally records embedding_backend=stub; the Phase 3 API checks the
backend as well as model/dimension to avoid mistaking hash vectors for Ollama.
Full-client persistent mode is optional; the tested deployment path uses the
pinned chromadb-client and Docker Chroma 1.0.12 over HTTP.

## Stage 1: extract

`pipeline/extract.py` uses pdfplumber page by page. Pages with fewer than 20
non-whitespace characters trigger Tesseract via Poppler at 200 DPI. Each raster
is closed after OCR. Successful OCR attempts set Page.ocr, including genuinely
blank pages that produce no text. Missing system tools produce a JSON warning
with source/page and explicit missing-text risk, rather than silently claiming
complete extraction. Other conversion failures fail the job.

The entrepreneurship policy requires OCR on all eight pages. Most interior
pages of the 2023 rules also need OCR. See CORPUS.md for font/text verification.
Blank/decorative pages may also trigger OCR; an OCR count is a count of attempts,
not a guarantee that every page yielded meaningful text.

Repeating non-clause edge lines on at least three pages and 60% of the document
are removed, along with isolated page numbers at the edges. Markdown headings,
numbered clauses and table lines are protected. This is deliberately conservative:
changing or infrequent headers can survive. It does not remove arbitrary text
from the middle of pages.

PDF table regions are extracted as pipe-delimited rows and excluded from prose
extraction to prevent duplicate, interleaved columns. HTML extraction excludes
navigation/header/footer/script/style content and retains headings and table
cells. Markdown front matter is removed before extraction; its version metadata
comes from discovery. `_index.json` is authoritative for the real downloaded
corpus, so exploratory files not listed there are excluded.

### Real table example

The fetched Fee Structure tuition table, flattened by naïve HTML text collection:

```text
Program
Fee
BBA / BS
Rs. 12,000
MBA / MS
Rs. 12,000
PhD
Rs. 12,000
```

The implemented extractor produces:

```text
| Program | Fee |
| --- | --- |
| BBA / BS | Rs. 12,000 |
| MBA / MS | Rs. 12,000 |
| PhD | Rs. 12,000 |
```

This preserves programme/amount associations. Merged cells are not expanded into
inferred repeated values; empty cells stay empty. OCR of scanned tables is text
only and cannot guarantee column recovery. PDF prose is retained before the
structured tables; exact visual reading order between them is not reconstructed.

## Stage 2: clean

`pipeline/clean.py` applies Unicode NFKC normalization, removes soft hyphens and
BOM/control artefacts, joins hyphenated line breaks before lowercase letters,
normalizes horizontal whitespace and collapses excess blank lines. It preserves
clause numbers such as 1.21/4.2, decimal values like 2.00, Markdown headings and
pipe delimiters. It returns a new document rather than modifying extraction data.
OCR character mistakes are not guessed or rewritten as policy facts.

## Stage 3: chunk

Units are **whitespace tokens**, not model-specific subword tokens. Structure mode
splits by Markdown/numbered/title headings and standalone clause markers, then
prefers paragraph boundaries, then sentence boundaries, then whitespace-token
windows. Every chunk is at most CHUNK_SIZE tokens. Neighbouring windows within
one section/page share CHUNK_OVERLAP tokens; overlap is not carried across
sections or physical pages. Section labels continue across page boundaries,
while each chunk cites its actual one-based physical page.

The fixed strategy uses plain token windows for later controlled failure tests.
Stable SHA-256 chunk IDs include source, version, page, position and content.
Unchanged input/settings reproduce the same IDs. Changes in content or chunking
produce new IDs, and storage removes obsolete IDs.

Storage amplification is total stored whitespace tokens divided by original
cleaned whitespace tokens, including headings in both counts. Empty documents
have amplification zero. Logs contain per-document and corpus-wide amplification.
For a verified 25-token fixed-window example with size 10/overlap 2, lengths are
10, 10 and 9, giving amplification 29/25 = 1.16.

The shipped 512/64 setting is provisional. Three-configuration recall tuning and
semantic-cache threshold experiments belong to Phase 4; no recall or threshold
result is claimed here.

## Stage 4: embed

`pipeline/embed.py` returns (vectors, embed_dim), validating count, consistent
nonzero dimension, finite values and nonzero vectors. Ollama /api/embed requests
use the exact EMBED_MODEL, batching 32 chunks by default with truncation disabled.
An overlong model input fails explicitly rather than silently losing text.

Stub mode hashes normalized lexical tokens into 384 signed buckets and normalizes
the vector. It is deterministic and invariant to token ordering, allowing cheap
fixture retrieval. It is neither a trained semantic model nor an evaluation of
nomic-embed-text. Ollama is mocked in unit tests; real Ollama inference is deferred
until the user's Windows installation is configured.

## Stage 5: store and invalidate

`pipeline/store.py` validates inputs before touching the index. Redis must respond
before index mutation. It clears only `rahbar:cache:*` using SCAN/DELETE, preserving
other Redis keys. The collection is marked index_state=building, receives upserts
in batches of 100, and loses obsolete IDs from the previous complete snapshot.
After a count check, cache invalidation runs again; only then is index_state=ready
published. A cache failure exits nonzero and leaves the index unready.

Collection metadata pins embed_model and integer embed_dim, with the legacy
`dimension` alias retained. It also contains embedding_backend, index_revision
and index_state. Cosine distance is configured at collection creation. Chroma
1.0.12 rejects hnsw:space in modify() even if unchanged, so immutable HNSW fields
are omitted from metadata updates; Chroma retains the configured distance space.

A model/dimension change recreates the collection after marking it unready.
This is a single-writer, in-place rebuild with a readiness maintenance window,
not an atomic snapshot swap. Interrupted writes can leave a partial collection
marked building; rerunning repairs it. The Phase 3 API checks index_state and the
model/dimension/backend pins, and binds cached answers to the index revision to
reject requests that race a rebuild. See docs/API.md. Do not overlap indexing jobs. These Phase 3 protections are now implemented in the API.

Every chunk stores:

| Field | Type | Meaning |
| --- | --- | --- |
| source | string | input document filename |
| section | string | detected heading/clause, or explicit fallback label |
| page | integer | one-based physical page; HTML/Markdown use 1 |
| doc_version | string | edition from manifest or fixture front matter |
| superseded | boolean | default retrieval exclusion for old policy editions |

CLI success is exit 0; invalid settings, empty corpus, embedding failures, storage
failures and cache outages exit 1 with a JSON error. `python -m pipeline.run`
remains the container pipeline entrypoint.

## Phase 2 verification

Unit tests cover extraction/OCR/missing tools, margin stripping, cleaning,
structure versus fixed chunking, exact overlap/amplification, metadata/IDs,
configuration, mocked Ollama batching/malformed vectors, model pin changes,
idempotent upsert, stale deletion, cache outages and CLI failures. Live Docker
Chroma/Redis fixture indexing twice produced the same 12 IDs, invalidated a seeded
cache entry and preserved an unrelated Redis key. Fixture amplification was 1.0.
Full-corpus smoke indexing passed with real WSL OCR and live Docker services:

| Document | Chunks | OCR attempts |
| --- | ---: | ---: |
| Academic Rules 2023 | 153 | 24 |
| Academic Rules 2026 | 211 | 5 |
| Prospectus academic rules | 17 | 0 |
| Annual Report 2019-20 | 187 | 0 |
| Annual Report 2023-24 | 344 | 0 |
| Fee Structure HTML | 13 | 0 |
| Grading HTML | 10 | 0 |
| Entrepreneurship policy | 58 | 8 |
| Total | 993 | 37 |

At 512/64, corpus amplification was 1.011830280969173. The run took 105.2 seconds
and exited zero. The five OCR attempts on the 2026 rules include near-empty pages,
unlike the four completely empty pages identified in Phase 1.
Collection rahbar_phase2_corpus contains 993 rows pinned to stub/384, state=ready.
A scaled-vector query returned cosine distance 0.0, confirming cosine configuration
survives metadata updates. Fixtures live in rahbar_phase2_fixtures. These are
smoke-test collections, not a production nomic index. Detailed logs remain in
ignored corpus/raw/phase2-full-index.jsonl; essential results are recorded here.
No evaluation baseline or generation metric is produced in this phase.


## Phase 4 measured production configuration

The Phase 2 smoke numbers above are historical stub results. Final extraction
clips PDF characters to visible page bounds, uses Tesseract PSM 6 for aligned
clause text, normalizes clause section labels, and merges heading-only fragments
into the following facts. These fixes were driven by actual off-page characters
at x=-376 and the CI repeating-course question retrieving headings without facts.
No policy values or OCR-ambiguous clause numbers were guessed.

| Size | Overlap | Strategy | Chunks | Amplification | Recall@3 | Recall@5 |
| ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 256 | 32 | structure | 945 | 1.0411 | 0.9375 | 0.9375 |
| 512 | 64 | structure | 875 | 1.0129 | 0.9375 | 0.9375 |
| 1024 | 128 | structure | 862 | 1.0000 | 0.9375 | 0.9375 |
| 100 | 0 | fixed | 748 | 1.0000 | 0.2500 | 0.2500 |

The golden set was frozen before these experiments. These figures use real nomic
embeddings and actual Chroma retrieval; generation is not part of the chunking
comparison. Select 512/64: recall tied across structure settings, it preserves
context with shorter worst-case evidence than 1024 and less overhead than 256.
Units remain whitespace tokens, not model subword tokens. With 16 answerable
questions, one miss changes recall by 6.25 percentage points; this is a small
in-sample calibration set, not a held-out quality guarantee.

| Cache threshold | True hits (3 positive pairs) | False hits (5 negative pairs) |
| ---: | ---: | ---: |
| 0.80 | 3 | 1 |
| 0.90 | 2 | 0 |
| 0.95 | 1 | 0 |

Ship 0.90, the lowest tested threshold with zero false hits. Graduation versus
warning CGPA similarity 0.8059 rules out 0.80. The graduation paraphrase at
0.8866 misses the shipped threshold; this is the accepted safety/hit-rate tradeoff.
The CI hash-embedding fixtures separately use RELEVANCE_FLOOR=0.15, calibrated
at 0.15/0.25/0.35 in eval/fixture-calibration.json. Production remains 0.35.
Do not mix fixture and full-corpus baselines or interpret hash quality as nomic quality.

Evaluation matches exact source plus normalized clause label (Clause 1.21 and
1.21 plus descriptive text denote the same clause). Non-clause headings match
normalized case/whitespace; distinct titles such as 9. Privacy and 9. Retakes are
not conflated. Citation validity uses exact source/section/page triples, not that
clause normalization. Must-abstain questions have undefined retrieval recall and
are excluded from its mean. Generation validity weights individual citations.
The gate rejects recall@5 drops greater than 0.05, citation validity below 0.95,
or abstention correctness below 1.0. Missing metrics/baselines fail closed unless
a first baseline is explicitly requested; failed gates cannot overwrite baselines.

Full results/baseline are in eval/results.json and eval/baseline.json. Fast CI
uses eval/fixtures/golden.fixture.yaml and baseline.fixture.json instead. The
runner defaults to cache bypass so metrics reflect actual retrieval/generation.
See docs/EVALUATION.md for reproduction and limitations.


### Measured local memory improvement

A full-corpus WSL stub index run peaked at 1,083,120 KiB RSS before releasing
pdfplumber layout/character caches page by page. Explicitly closing both visible
and original pages reduced the measured peak to 165,492 KiB (about 161.6 MiB).
Both runs completed successfully with real OCR. These are GNU time local-process
measurements, not Kubernetes pod peaks or real-model server memory. Ollama runs
separately. Actual cluster samples and container limits are recorded in
docs/evidence/public-corpus-kubernetes-runtime.json. See also
eval/experiments.json resource_sample for the local process measurements.


Original local evaluation: recall@3/5=0.9375, citation validity=1.0 (28/28),
abstention correctness=1.0 (2/2). Fifteen of sixteen answerable questions were
supported; the current-version Clause 4.3 retrieval miss remains visible. Final
local collections are rahbar_policies (875 real-model chunks) and
rahbar_ci_fixtures (16 hash-fixture chunks); obsolete smoke/tuning collections
and the temporary embedding-vector cache were removed.
