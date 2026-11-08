# AI usage disclosure

The team used Codex and Antigravity for implementation assistance, debugging,
tests, deployment verification and documentation. The students coordinated the
work, ran checks, configured their accounts/services, supplied screenshots and
controlled GitHub pushes, reviews and merges.

| Tool | Assistance | Verification |
| --- | --- | --- |
| Codex | Corpus selection/fetching, SHA-256 manifest, extraction/OCR, chunking and embeddings | Actual public documents, checksums, page counts, OCR and table checks; pipeline tests |
| Codex | Retrieval, generation providers, citation validation, semantic cache, probes and metrics | Offline tests, real Chroma/Redis checks, model-pin failure and injection/refusal tests |
| Codex | Golden sets, evaluator, tuning and failure analysis | Real embedding/generation experiments, frozen baselines, separate fictional CI fixtures |
| Codex | Docker/Kubernetes configuration, CI/CD, network diagnosis and local run configuration | Image builds, rendered/schema-checked manifests, workflow checks, network regression tests and live public-corpus deployment |
| Antigravity | Continuation of deployment debugging, fixture acceptance and resource/evidence collection | Recorded Ingress, persistence, cache invalidation, idempotent indexing, model-pin, HPA and rollout checks |
| Ollama | nomic-embed-text embeddings and llama3.2:3b answer generation | Model names/digests in eval/model-manifest.json; measured answers in eval/results.json |

The final public-corpus Kubernetes evaluation indexed 875 chunks including 37
OCR pages. Recall@5 was 0.9375, all 29 returned citations matched retrieved
references, and both absent-topic questions were refused. Fifteen of sixteen
answerable questions were answered. The retained current-version retrieval miss
is documented rather than hidden. Citation-reference membership is not proof of
semantic entailment or general policy accuracy.

The CI corpus is fictional and uses deterministic stub embeddings/generation
with real Chroma and Redis. Its baseline is separate from the full public-corpus
baseline. A real temporary fixture-heading regression failed the recall gate;
restoring the heading restored passing checks. Frozen baselines were not changed
to disguise that failure. GitHub screenshots were supplied by a human.

Actual debugging included immutable Chroma metadata, PDF layout/OCR issues,
retained extraction memory, injected service environment variables, image export,
Ingress routing, model-overlay namespaces, overlapping pod/host addresses and
tool-download outages. The reported fixture memory and independently sampled
full-corpus memory are distinguished in ENGINEERING-NOTES.md and evidence files.
No final Kubernetes memory peak or hour-long incident is invented.

AI assistance also produced tests and the local run instructions. CI installs
small tools from pinned Go modules and extracts pinned Trivy from its official
image, caching the binaries to reduce dependence on release-download services.
All scan, schema, test and evaluation gates remain enforced. Students must verify
the actual successful CD run and published SHA tags before submission.

No claim is made that a human manually audited every PDF page or model response.
Final interpretation, academic review and submission remain the students'
responsibility. No private student data or credentials were added. Credentials
come from environment variables or GitHub Secrets. Downloaded PDFs, environments,
runtime state and the personal viva guide are excluded from deliverable commits.
Only the two required local models were downloaded; their weights are not in Git.
