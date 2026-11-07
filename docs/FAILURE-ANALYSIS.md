# Intentional failure analysis

These four failures were actually exercised against the same public corpus and pinned nomic embeddings. Measurements are in `eval/experiments.json`. The golden set was fixed first. Temporary tuning collections were removed afterward; the production collection and embedding pin were restored.

## A. Extraction: switch off OCR

With OCR enabled the eight-page entrepreneurship policy produced 71 chunks. With `enable_ocr=False`, extracted characters and chunks both fell to zero. All eight pages generated `ocr_disabled` JSON messages with source/page and an explicit missing-text risk. Fonts were already verified absent in Phase 1.

Example logged event (same keys as the actual run):

```json
{"msg":"ocr_disabled","source":"faculty-entrepreneurship-and-technical-start-ups-policy.pdf","page":1,"loss":"page text may be missing"}
```

Diagnosis: an apparently successful PDF open is not evidence of text recovery. Inspect per-page text length and OCR diagnostics before blaming the embedding model. Remedy: enable OCR, install Tesseract/Poppler, keep the recovered page flag and verify OCR samples. Blank pages may also trigger OCR; count attempts separately from recovered facts. Missing OCR tools produce explicit loss warnings rather than fabricated text.

## B. Chunking: fixed 100-token windows, zero overlap

Structure 512/64 gave recall@3=0.9375, recall@5=0.9375, 875 chunks, amplification=1.0129. Fixed 100/0 gave recall@3=0.2500, recall@5=0.2500, 748 chunks, amplification=1.0. The recall@5 decrease was 68.75 percentage points.

Physical PDF page 53 contains the long privacy/data-security definition. A measured fixed-window boundary was:

```text
classified as Sensitive or Confidential into AI tools not supported by the University. Additionally, datasets containing information indirectly
[WINDOW BOUNDARY]
identifying individuals must not be submitted to unsupported AI tools. Furthermore, ensuring accuracy and integrity of information is
```

Diagnosis: fixed windows break clauses and mix adjacent topics; they also attach the section active at the window start, so reference-based recall reflects both context splitting and section attribution. The decline must not be attributed solely to semantic loss. Remedy: section/paragraph/sentence boundaries and overlap within a section. In the final chunker, heading-only fragments enrich the following clause instead of consuming a top-k slot.

## C. Retrieval compatibility: deliberately break the embedding pin

The collection embed_model was temporarily changed to deliberately-wrong-embedding while the running API remained nomic-embed-text/768. Readiness and queries returned 503; liveness returned 200. Redis remained healthy. The exact original metadata was restored in a finally block and readiness returned 200. Request ID: failure-C-demo.

Actual structured conflict log:

```json
{"ts": "2026-11-07T13:38:42Z", "level": "ERROR", "logger": "rahbar.retrieval", "msg": "embedding_pin_mismatch", "request_id": "failure-C-demo", "api_embed_model": "nomic-embed-text", "collection_embed_model": "deliberately-wrong-embedding", "api_embed_dim": 768, "collection_embed_dim": 768, "api_embedding_backend": "ollama", "collection_embedding_backend": "ollama"}
```

Diagnosis: compare api_embed_model, collection_embed_model, dimensions and backend, not just network reachability. Matching dimensions do not imply matching vector space. Remedy: configure API/indexer together and reindex with the intended model. The API stays alive to expose the conflict; restarting it cannot repair incompatible vectors.

## E. Source/version: remove the superseded filter

The test question asked whether students may exceed five courses provided they do not get ahead of their batch, without explicitly requesting an old policy. The same query embedding was submitted with and without superseded=false. With the filter disabled, the old 2023 Clause 4.3 was top-ranked; the current policy restricts an extra course to final-year students.

| Mode | Rank | Source | Section | Superseded | Similarity |
| --- | ---: | --- | --- | --- | ---: |
| filtered | 1 | academic-rules-handbook-jun-2026.pdf | Clause 6.6 | False | 0.7651 |
| filtered | 2 | academic-rules-handbook-jun-2026.pdf | Clause 6.11 | False | 0.7548 |
| filtered | 3 | academic-rules-handbook-jun-2026.pdf | Clause 1.19 | False | 0.7547 |
| filtered | 4 | academic-rules-handbook-jun-2026.pdf | Clause 1.20 | False | 0.7397 |
| filtered | 5 | academic-rules-handbook-jun-2026.pdf | Clause 4.5 | False | 0.7335 |
| filter_disabled | 1 | undergraduate-academic-rules-aug-2023.pdf | Clause 4.3 | True | 0.8682 |
| filter_disabled | 2 | undergraduate-academic-rules-aug-2023.pdf | Clause 1.19 | True | 0.7767 |
| filter_disabled | 3 | undergraduate-academic-rules-aug-2023.pdf | Clause 1.20 | True | 0.7718 |
| filter_disabled | 4 | academic-rules-handbook-jun-2026.pdf | Clause 6.6 | False | 0.7651 |
| filter_disabled | 5 | academic-rules-handbook-jun-2026.pdf | Clause 6.11 | False | 0.7548 |

The filtered run excludes old editions, but its top five did not include current Clause 4.3 for this old-rule-biased wording. Version filtering prevents the stale source; it does not magically solve retrieval completeness. Diagnosis: inspect source/version metadata and retrieved IDs, not just a fluent answer. Remedy: retain explicit version filters, allow historical queries intentionally, and improve retrieval coverage using broader evaluation or hybrid lexical search rather than silently serving a repealed clause.

## Additional extraction diagnosis and resource check

The 2026 PDF contains characters with x positions around -376, outside the visible page. Extracting the full object layout imported text from facing pages. Restricting extraction to the visible bounding box removed this contamination. OCR PSM 6 also kept old clause numbers next to their words. Regression tests use a tiny PDF with deliberately off-page text and a real OCR-style comma after Clause 4.3. No uncertain OCR number such as 44 was guessed to be 4.4.

All experiments measure this local corpus/setup. They are not evidence that the Kubernetes cluster has been deployed. Real cluster logs, memory margins and screenshots are Partner B integration evidence.

The local full-corpus resource experiment exposed retained PDF layout caches: peak
RSS fell from 1,083,120 KiB to 165,492 KiB after explicit per-page close. Both runs
exited zero. This is a measured local improvement, not a Kubernetes resource claim.


## Additional generation-schema incident (D/F)

The first real small-model evaluation passed the three safety/retrieval gates,
but only 1/16 answerable questions returned answered_from_context=true. Inspection
showed a supported 2.00 CGPA answer with five valid citations and high confidence
incorrectly labelled answered_from_context=false. The consistency validator rejected
it and the retry, producing a safe refusal. This exposes a limitation of the gate:
valid citations/abstentions do not by themselves guarantee useful answer coverage.
The initial aggregate is preserved in eval/initial-generation-diagnostics.json.

Explicit SUPPORTED/UNSUPPORTED output modes and a Boolean-field description fixed
the inconsistent flag. The validator was not weakened or coerced. A follow-up
inspection also checked that restrictions limited to a second warning were not
generalized to every student on warning; the prompt now requires subgroup/exception
scope, and a generic multipart-rule safeguard quotes retrieved clauses with
different obligation levels instead of trusting a model paraphrase. Constructed
citations are revalidated; instruction-like poison is excluded. Final responses and the
answered flag rate are recorded in eval/results.json, not inferred from schema
validity alone. This does not establish semantic correctness for every future answer.
