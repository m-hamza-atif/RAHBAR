# Query service (Phase 3)

The API reads an existing index. It never fetches documents or runs indexing at
startup. Run the indexer separately before using RETRIEVER=chroma.

## Local WSL run

From the repository root, with the existing Docker Chroma and Redis containers:

```bash
export RETRIEVER=chroma LLM_PROVIDER=stub EMBED_MODEL=stub
export CHROMA_HOST=localhost CHROMA_PORT=8001
export CHROMA_COLLECTION=rahbar_ci_fixtures
export REDIS_HOST=localhost REDIS_PORT=6379
export REDIS_FAKE=false
export RELEVANCE_FLOOR=0.15
PYTHONPATH=api .venv-wsl/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
curl -s http://localhost:8000/healthz
curl -s http://localhost:8000/readyz
curl -s http://localhost:8000/metrics
curl -s http://localhost:8000/api/ask -H 'Content-Type: application/json' -d '{"question":"When is a student placed on academic warning?"}'
```

The fixture institution is fictional. Stub responses are extracted test evidence,
not authoritative FAST policy advice or real model inference. API and indexer
must agree on collection, embedding model, dimension and backend. The default
collection is rahbar_policies; this command explicitly selects the fixture index.

## Query sequence

1. Read collection readiness/revision and ping Redis. Unavailable dependencies
   produce HTTP 503; liveness remains independent.
2. Embed using the same lexical hash algorithm as the indexer in stub mode,
   or the configured Ollama embedding model. No indexer modules are imported by
   the production API. EMBED_DIM defaults to 384 for stub embeddings, otherwise
   768 for the default nomic model; override for a different real model.
3. Look up a semantic cache match unless this is a follow-up. Cache entries are
   scoped by collection, index revision, model/dimension, provider/model and
   retrieval/generation settings. Explicit years/numbers and negation must also
   match. Redis entries expire after CACHE_TTL (default 3600 seconds); at most
   256 candidates are scanned for a query.
4. Retrieve TOP_K passages. Default filtering is superseded=false. Explicit year
   requests select matching version prefixes; historical/comparison requests
   relax the superseded filter. Version scope comes from the current question,
   not stale years in conversation history. Convert cosine distance to clamped
   similarity and remove passages below RELEVANCE_FLOOR (default 0.35).
5. If no passages clear the floor, abstain without calling the generator. Otherwise
   delimit and escape evidence, label it untrusted, and request Answer JSON.
6. Parse with Pydantic, then verify each citation's source/section/page against
   the retrieved evidence. Retry once with correction instructions. A second
   failure returns a safe HTTP 200 abstention and increments fallback_total.
7. Recheck revision after retrieval and generation; a rebuild race returns 503.
   Only first-attempt validated, grounded, standalone responses are cached.
   Cache hits receive the current request ID. Cache keys from an old revision
   cannot be reused even if a late write races indexer invalidation.

## Providers and request contract

Supported LLM_PROVIDER values: stub, ollama-host, ollama-incluster and hosted.
Ollama uses /api/chat with the Answer JSON schema and configured temperature.
Its embeddings use /api/embed with silent truncation disabled. OLLAMA_BASE_URL
is preferred; OLLAMA_URL remains an alias. The default host.minikube.internal
endpoint falls back to localhost only on transport failure. The application does
not install Ollama or download models. The user's preferred real installation
is on Windows; no Windows installation was changed during Phase 3.

Hosted mode needs HOSTED_BASE_URL, LLM_MODEL and LLM_API_KEY from the environment.
The base URL must include the provider's OpenAI-compatible version path; the API
appends /chat/completions. JSON-object mode plus the full schema in the system
prompt supports compatible Groq, OpenRouter and Gemini endpoints. Credentials
are not written to files or logged. Hosted generation still needs a matching
embedding backend; it does not supply an embedding model automatically.
Live provider inference has not been verified; HTTP payloads and parsing are
tested with mocked endpoints. Stub generation is deterministic extraction with
injection-line rejection, not a production semantic model.

POST /api/ask still accepts {"question":"..."}. It additionally accepts optional
history with user/assistant role and content fields; history skips semantic cache
reads/writes. Questions are 3-500 characters and must have at least three characters
after trimming. History is bounded to 20 messages of 2000 characters each. The
response preserves all starter fields and adds cached=false/true. Internal
reasoning is a brief evidence summary and is never returned. See ADR 0005.

## Readiness and diagnostics

GET /healthz returns {"status":"alive"} without touching Chroma, Redis or the LLM.
GET /readyz checks the collection exists, has rows, is marked ready, has a revision,
and matches embed_model, embed_dim and embedding_backend; Redis must also ping.
Conflicts return 503 with named checks and explicit JSON conflict logs. Startup
runs the same read-only checks but keeps the process alive when dependencies
fail, so probes can explain the failure. RETRIEVER=stub explicitly reports a
simulated index; only REDIS_FAKE=true enables an in-memory test cache. There is
no automatic in-memory cache fallback when a real Redis connection fails.

Each query logs request_id, top_k, retrieved_chunk_ids, similarity_scores,
cache_hit and abstained. X-Request-ID is echoed or generated. Prometheus exposes
requests/latency, retrieval/generation latency, cache hits/misses/ratio, abstentions,
fallbacks and prompt/completion token counters. Remote provider usage is used
when supplied; stub/missing usage uses whitespace estimates, not billing counts.
The cache ratio is local to an API process and should be aggregated accordingly.

## Verification and limits

Offline tests cover normal/cached answers, historical filtering, absent topics,
indexed poison, retry/fallback, fake citations, cache exclusions, revision races,
readiness failures, startup conflicts, prompt escaping, provider payloads and
matching indexer/query stub vectors. Live checks also used Docker Chroma 1.0.12
and Redis 7.4.2 with a dedicated 13-row fixture-plus-poison collection. They
verified current 80% versus historical 75% attendance, 2.00 academic warning,
honest hostel abstention, poison rejection, Redis hit and model-pin 503 with
liveness still 200. The collection pin was restored afterward.

The 0.35 relevance floor and 0.90 cache threshold are provisional. For example,
the short stub query "What attendance was required in 2023?" retrieves the correct
old edition at similarity about 0.152, below the floor, and safely abstains.
A more descriptive historical question scores about 0.683 and answers. Do not
interpret smoke tests as full recall, production-model quality or threshold
calibration. Those measurements and the CI evaluation gate belong to Phase 4.

Tests with coverage (from repository root):

```bash
.venv-wsl/bin/python -m pytest api/tests --cov=api/app --cov-fail-under=65
```


## Phase 4 production verification and scope preservation

The real-model profile is documented in EVALUATION.md: nomic-embed-text/768,
llama3.2:3b, production relevance floor 0.35 and cache threshold 0.90. The local
CI example above intentionally uses hash embeddings and floor 0.15. Full and
fixture results/baselines are separate. X-Cache-Bypass=true skips both cache
reads and writes for reproducible evaluation. Readiness exposes non-secret
configuration/revision for provenance, not credentials.

The prompt now explicitly distinguishes supported=true from refusal=false and
provides exact citation objects. The internal evidence summary is capped at 300
characters; useful conditions belong in the answer. For cited multipart clauses
with different must/should/may levels, services/grounding.py returns the verbatim
retrieved clauses and their actual page citations rather than trusting a
paraphrase that may strengthen recommendations or drop a subgroup restriction.
Known instruction-like poison is never copied by that helper. Its constructed
citations pass the same validator. Schema/provider failures use a verification
failure message rather than falsely claiming the corpus lacks the topic.

Temporary verification servers were stopped after testing and model memory was
unloaded. Start the service explicitly with the runbook when needed. Obsolete
phase2/phase3 smoke collections have been retired; use the current CI collection
above or the real-model production collection in EVALUATION.md.
