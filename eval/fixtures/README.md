# CI fixtures

Three short Markdown documents for the `e2e-eval` job (section 6), so CI can index
a corpus and score recall in a minute instead of six. The institute is fictional.

| File | Why it is here |
| --- | --- |
| `academic-rules-2023.md` | The superseded version (75% attendance, CGPA 1.75, grade cap B) |
| `academic-rules-2026.md` | The current version (80%, 2.00, no cap), plus one planted injection line |
| `fees-2026.md` | Two tables and exact-term numbers |

The hostel topic is missing on purpose: `golden.fixture.yaml` asks about it and
expects the service to decline.

Use `CORPUS_DIR=eval/fixtures` from the repository root (or an absolute path in
containers). These fictional facts must never be presented as FAST-NUCES policy.
Keep the planted instruction in section 3.2: it is untrusted test evidence for
the injection defence, not an instruction to the indexer or assistant.

Each file starts with front matter (`doc_version`, `superseded`). The indexer's
`discover()` reads it when there is no `_index.json`, so your extract stage
needs to handle `.md` files as well as PDFs.

Phase 4 uses seven questions, including an explicit 2023 attendance query.
Clause facts now cite stable labels such as `Clause 1.1`; headings enrich the
following clause instead of creating empty policy chunks. The CI profile uses
`RETRIEVER=chroma`, `EMBED_MODEL=stub`, `EMBED_DIM=384`, `LLM_PROVIDER=stub`,
`RELEVANCE_FLOOR=0.15`, and reachable Chroma/Redis. Its baseline is
`baseline.fixture.json`, never the full-corpus `../baseline.json`.
See `../fixture-calibration.json` for the measured floor comparison and
`../../docs/EVALUATION.md` for complete CI commands.
