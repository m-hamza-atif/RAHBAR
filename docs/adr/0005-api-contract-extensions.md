# ADR 0005: additive history/cache fields and strict citation pages

Status: implemented in Partner A Phase 3.

The starter UI and evaluation runner consume the existing AskResponse fields.
Follow-up cache exclusion requires an explicit way to submit conversation history,
and the UI already supports a cached indicator. We retain every existing response
field and single-question request while adding optional history (default empty)
and cached (default false). History messages allow only user/assistant roles and
have size limits. Clients that send only question continue to work.

Citation.page is now a required positive integer, matching indexer physical-page
metadata and the assignment's source/section/page verification requirement. A
generator cannot omit or invent a page and still pass citation validation. All
existing fixtures/stub passages supply valid pages. Internal Passage/ RetrievedRef
types retain the starter optional-page shape, but a grounded generated citation
must identify an actual page. Strict Answer/Citation validation rejects extra
model fields and type coercion rather than hiding malformed output.

The existing reasoning field is retained for schema compatibility and requested
as a brief evidence summary. It is never serialized into AskResponse or the cache's
response payload; private reasoning is neither requested nor exposed.
Phase 4 caps this internal summary at 300 characters to preserve a bounded
generation budget for the actual answer and its policy conditions.

Evaluation additionally uses the optional X-Cache-Bypass request header, which
skips cache reads and writes without changing the question/response shape.
Readiness includes non-secret configuration and revision information so evaluation
records its model/index provenance; no credential fields are exposed.

The provider interface additionally accepts validation feedback and may return
raw JSON with token usage. Central validation performs the same retry/citation
checks for all providers. Provider implementations and callers were updated
together. The route and port contract remains compatible: POST /api/ask and the existing
probe endpoints remain unchanged.
