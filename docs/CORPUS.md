# FAST-NUCES corpus

Phase 1 audit: 7 November 2026. Sources are public university documents, discovered
from https://www.nu.edu.pk/Downloads and the university's student/ORIC pages.
The selected corpus contains **8 documents: 6 PDFs (215 physical PDF pages) and
2 HTML pages**. HTML is not counted toward the page minimum. Files were actually
downloaded and parsed; the checksums below identify the measured snapshots.

## Document inventory

| Document | Version | Superseded | File | Bytes | SHA-256 | URL | Pages | Properties |
| --- | --- | --- | --- | ---: | --- | --- | ---: | --- |
| Undergraduate Academic Rules (Aug 2023) | 2023-08 | yes | `undergraduate-academic-rules-aug-2023.pdf` | 14,888,226 | `cddfe1f5e9770132e27d686abd1c2e6742ef4732f0c2f431ed514bc1691d2004` | <https://nu.edu.pk/public/downloads/Academic-Rules-Undergrad-Aug-2023.pdf> | 26 | 1, 2, 5, 7 |
| Academic Rules Handbook (Jun 2026) | 2026-06 | no | `academic-rules-handbook-jun-2026.pdf` | 987,731 | `4cfee3e191b84aeb9168f17656c7642212ff52b90f2780d028b33c154aa74b62` | <https://nu.edu.pk/public/downloads/Academic_Rules_Handbook_2026.pdf> | 58 | 1, 2, 5, 7 |
| Prospectus 2026 - Academic Rules and Regulations | 2026 | no | `prospectus-2026-academic-rules-and-regulations.pdf` | 7,066,767 | `a7e7f6896a59eb9413c9e8826e6c4c018ebe52045d10cebfcba92ded10a3174a` | <https://nu.edu.pk/Admissions/ProspectusUpload/Academic%20Rules%20and%20Regulations.pdf> | 5 | 1, 5, 7 |
| Annual Report 2019-20 | 2019-20 | no | `annual-report-2019-20.pdf` | 891,216 | `4d1961e340b13273bb039805ab5fd5e2c7bd0144a5bd5870f2ce4da13becd650` | <https://nu.edu.pk/public/downloads/AnnualReportForm/Annual%20Report%202019-20.pdf> | 33 | 1, 4, 7 |
| Annual Report 2023-24 | 2023-24 | no | `annual-report-2023-24.pdf` | 5,100,456 | `3c9d89e84af24df4b939f10e32c620a3877b276acea1db52f1aae4098e5c057a` | <https://nu.edu.pk/public/downloads/AnnualReportForm/Annual%20Report%202023-24.pdf> | 85 | 1, 4, 7 |
| Fee Structure page | 2026-27 | no | `fee-structure-page.html` | 91,429 | `ec8872ae77cac7e96e20e6979933f36b00aaeb0ab3f668a2116e521c655e7b90` | <https://www.nu.edu.pk/Admissions/FeeStructure> | 0 | 4, 7 |
| Grading page | 2026 | no | `grading-page.html` | 95,673 | `66a995b4d8474e914d37bfa14755a5361f47327d5a7314f9b7ec15d9b6176e6e` | <https://www.nu.edu.pk/Student/Grading> | 0 | 4, 7 |
| Faculty Entrepreneurship and Technical Start-ups Policy | 2022-05 | no | `faculty-entrepreneurship-and-technical-start-ups-policy.pdf` | 3,872,809 | `c2d5c7648d1593daf34d5c0596ede476e8984b0551830cc1690017e6e22f1359` | <https://nu.edu.pk/OricResources/ResearchPolicies/27.pdf?20220530> | 8 | 1, 3, 5 |

`corpus/sources.yaml` is the curated input. `corpus/MANIFEST.md` is generated;
`corpus/raw/_index.json` preserves filename, source URL, checksum, physical page
count, pages with no extracted text, `doc_version` and Boolean `superseded` for
the existing indexer discovery contract. Downloaded bytes and temporary audit
outputs stay under the ignored `corpus/raw/` directory. Commit sources, fetcher,
requirements and manifest, never the downloaded PDFs.

## Seven required properties and reachable failures

| # | Property | Exact evidence | Failure or experiment enabled |
| --- | --- | --- | --- |
| 1 | At least six documents and forty pages | Six PDFs: 26 + 58 + 5 + 33 + 85 + 8 = 215; plus two HTML documents | Enough independent sources for retrieval and citation checks |
| 2 | Two editions of one policy | Undergraduate Academic Rules August 2023 versus June 2026; section 4.3 on PDF pages 14 and 19 respectively | Source failure E: stale course-load advice if superseded filtering is disabled |
| 3 | Image-only PDF | Faculty Entrepreneurship and Technical Start-ups Policy: all eight pages have empty extracted text and no fonts | Extraction failure A: zero substantive chunks if OCR is disabled |
| 4 | Information-bearing tables | Fee Structure HTML, Tuition Fee and Fee Refund Policy tables; Grading HTML, Letter grades for BBA & BS programs; Annual Report 2023-24 PDF page 73, Table 6, corrective actions by campus | Extraction A: flattening loses row/column associations; exact retrieval C |
| 5 | Long clauses | Academic Rules 2026 section 4.4, PDF pages 19-20 (printed 13-14), subclauses a-e; sections 4.5-4.11 continue on PDF page 20 | Chunking B: short fixed windows separate the warning condition from its restrictions; test section-first splitting and overlap |
| 6 | Deliberately absent detailed policy | No Transport and Hostel Facilities PDF, no Hostel & Transport Rules, no full Student Handbook in sources or index | Honest abstention for hostel curfew, mess refunds and room allocation; never infer these from a campus description |
| 7 | Exact terms | 2026 Rules PDF page 10 (printed 4), clauses 1.21, 1.22, 1.25; PDF page 24 (printed 18), clauses 5.4-5.6; fee HTML tuition table | Hybrid/exact-term retrieval motivation: punctuation and numbers can be poorly distinguished by dense similarity alone |

The property numbers in the inventory identify candidate documents, not a claim
that every page supports every property. Property 6 is corpus-wide exclusion,
not content belonging to any selected file. The actual assignment PDF is not in
this repository; this mapping follows the seven properties in the supplied
Partner A prompt and the starter contract.

## Version mapping and verified differences

For this retrieval dataset, set the August 2023 rules to `doc_version: "2023-08"`,
`superseded: true`; June 2026 rules to `doc_version: "2026-06"`,
`superseded: false`. This is the dataset's precedence rule for ordinary current
questions, not a legal assertion about every student's admission cohort.
Historical questions must explicitly select the earlier edition in Phase 3.
Annual reports describe different historical periods and both remain
`superseded: false`: a newer report does not repeal older historical facts.
The ORIC version label `2022-05` comes from the published URL query, not a
verified effective date; the PDF metadata modification timestamp is September
2024. The grading page is a 2026 retrieval snapshot; it has no verified policy
revision date. Fee Structure explicitly labels academic year 2026-27.

Two concrete comparisons, checked using OCR for the older edition:

* **Course load, section 4.3:** 2023 PDF page 14 (printed 9) permits more than
  five courses provided students do not get ahead of their batch. 2026 PDF
  page 19 (printed 13) permits one additional course for a final-year student,
  inclusive of FYP. Use this as the primary version-sensitive evaluation pair.
* **Semester length, section 1.6:** 2023 PDF page 6 (printed 1) specifies 15/16
  teaching weeks and two final-exam weeks. 2026 PDF page 7 (printed 1)
  specifies 16 teaching weeks, one makeup week and two final-exam weeks.

Do not copy the fictional fixture differences into FAST policy answers: for
example, the real older graduation clause 1.26 already requires 2.00 CGPA.
The newer clause is 1.25, not evidence that the numeric threshold changed.

## OCR verification and extraction limitations

Run from the repository root inside Ubuntu WSL:

```bash
pdffonts corpus/raw/faculty-entrepreneurship-and-technical-start-ups-policy.pdf
pdfinfo corpus/raw/faculty-entrepreneurship-and-technical-start-ups-policy.pdf
```

Actual `pdffonts` output contains only these header lines and no font rows:

```text
name                                 type              encoding         emb sub uni object ID
------------------------------------ ----------------- ---------------- --- --- --- ---------
```

`pdfinfo` reports 8 pages, A4, unencrypted, 3,872,809 bytes. In addition,
`pypdf` returns empty text on pages 1-8 and finds one image XObject on each
page. Thus this is an image-only document,
not merely an empty text extraction guessed from its title. The fetcher's
`no_text_pages` records measurements without executing the Phase 2 pipeline.

The 2023 rules are a **mixed PDF**: font rows exist for the cover/back cover,
but pages 2-25 have no extracted text. A document-wide font check alone would
miss this OCR requirement. OCR samples on PDF pages 6, 8, 13 and 14 recovered
substantive academic rules, including the verified differences above. Page 3
is blank, illustrating that a no-text page can also be a blank page.
The 2026 rules have no text on pages 2 and 56-58; Phase 2 should distinguish
blank/decorative pages from meaningful scanned pages and log the outcome.

For an OCR spot-check without persisting raster files:

```bash
pdftoppm -f 14 -l 14 -scale-to 2200 -singlefile corpus/raw/undergraduate-academic-rules-aug-2023.pdf | tesseract stdin stdout
```

This audit does not implement indexing, claim OCR accuracy for all pages, or
report retrieval metrics. Those belong to later phases. Physical PDF page
numbers above are one-based and include covers. The printed page labels differ;
store physical pages in citation metadata to make citations reproducible.

## Tables and exact-term probes

The fetched fee table lists BBA/BS, MBA/MS and PhD tuition at PKR 12,000 per
credit hour, effective Fall 2026. Its refund table has five rows: through day
10 (100%), day 15 (80%), day 20 (60%), day 30 (50%), then no refund from day 31.
Keep each programme/amount and deadline/percentage association together.
Annual Report 2023-24 Table 6 (PDF page 73) maps CFD, ISB, KHI, LHR and PWR to
7, 7, 12, 9 and 5 corrective actions respectively. These provide concrete
before/after table examples for the Phase 2 extraction work.

For exact-term questions use clause 1.21 attendance, clause 1.25 graduation
CGPA 2.00, and clause 5.4 academic warning CGPA 2.00. Clause 1.21 prescribes
100% attendance with a maximum 20% absence condonable by the HoD for genuine
reasons; avoid simplifying it to unconditional permission to miss 20%.
No invented course codes are added to the real corpus.

## Absent-topic boundary

Exclude the standalone Transport and Hostel Facilities PDF and detailed hostel
rules. The full Student Handbook was initially downloaded during discovery but
removed from the curated source list and `_index.json` to avoid importing
unwanted policy details. The indexer's existing `discover()` uses `_index.json`,
so orphan files in `raw/` are not indexed. Do not point discovery at an
unmanifested directory containing those exploratory downloads.
Annual reports contain incidental hostel/transport mentions in campus accounts;
these do **not** establish curfew times, mess fee refunds or room allocation.
Use narrowly phrased must-abstain questions about those missing details, not
claims that the corpus never contains the word hostel. Even the precise
transport/hostel PDF is intentionally never downloaded by the curated script.

## Reproduction and deterministic CI

```bash
uv run --no-project --with-requirements corpus/requirements.txt python corpus/fetch.py
uv run --no-project --with-requirements corpus/requirements.txt python corpus/fetch.py --verify
uv run --no-project --with-requirements corpus/requirements.txt python corpus/fetch.py --list https://www.nu.edu.pk/Downloads
```

The fetcher downloads sequentially with a two-second pause, bounded retries,
URL encoding, Drive viewer conversion, content validation and measured page
counts. It reuses only cached files whose checksums still match, preventing
silent reuse of tampered local files. `--force` deliberately refreshes all bytes;
review checksum changes before committing a new manifest. PDF URLs returning
HTML are rejected. Google Drive confirmation/login pages fail explicitly; the
selected corpus does not depend on Drive. HTML page counts are recorded as zero.

CI uses the existing **eval/fixtures/** directory (there is no root fixtures/
in the starter). Its three small committed Markdown documents already provide
a 2023/2026 version pair, exact 2.00/1.75 thresholds, tuition and charge tables,
and a deliberate injection line. The fictional institution is named explicitly.
`golden.fixture.yaml` includes ordinary, version, exact, abstention and injection
probes. No network or OCR is needed for these fixtures. The README is excluded
by indexer discovery. Future CI should set `CORPUS_DIR=eval/fixtures` from the
root, or use an absolute mounted path; preserve these filenames when uploading to the cluster.
