# ADR 0002: Redis semantic cache with revision-scoped entries

Status: implemented and measured.

Use Redis rather than another Chroma collection. Chroma is the indexer's write
boundary; API-owned cache writes should not turn the API into a policy-index
writer. Redis supports TTLs and namespace deletion and is shared across API
replicas. An in-memory dictionary exists only under explicit REDIS_FAKE=true
for isolated tests; Redis outages do not silently switch production to memory.

Each entry stores query_text, query_embedding, response_json and timestamp.
Keys include collection, index revision, model/dimension, generation provider/model,
and retrieval/generation settings. Search scans at most 256 entries and compares
cosine similarity. This bounded linear scan is appropriate for this assignment;
it is not a claim of a large-scale ANN cache implementation. Cache candidates
also preserve explicit year/number and negation scope. Entries expire after
3600 seconds by default. Indexer invalidation deletes only rahbar:cache:* with
SCAN/DELETE, before and after writes, preserving unrelated Redis keys.

The measured nomic-embed-text experiment tested eight query pairs. At 0.80,
three same-intent pairs hit but one distinct-intent pair falsely hit. Graduation
versus academic-warning minimum CGPA had similarity 0.8059. At 0.90 there were
two true hits and zero false hits; at 0.95 there was one true hit and zero false
hits. Ship 0.90: the lowest tested threshold with no false hits, accepting that
one valid paraphrase at 0.8866 misses. These are limited pairwise observations,
not a universal guarantee. All measured values are in eval/experiments.json.

Follow-ups/history skip reads and writes. Abstentions, unsupported output,
validation-retried responses and fallbacks are never cached. Cached citations
must match their saved retrieved references. Index revisions are checked around
retrieval/generation, and old-revision keys cannot be read after a rebuild even
if a late cache write races namespace invalidation. The evaluator bypasses cache
by default via X-Cache-Bypass=true to measure actual retrieval/generation.

Redis uses its persistent volume for restart persistence. Query
texts are retained in Redis, not stdout; logs contain identifiers/scores rather
than complete questions/evidence. The application intentionally handles public
policy content rather than private student records.
