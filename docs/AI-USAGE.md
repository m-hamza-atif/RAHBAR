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
