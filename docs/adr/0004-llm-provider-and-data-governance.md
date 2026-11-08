# ADR 0004: local model by default, pluggable structured generation

Status: implemented; final real-model measurements recorded in eval/results.json.

The query pipeline depends on a provider protocol rather than one SDK. Stub
mode is deterministic extractive synthesis for fast CI. Ollama uses /api/chat
with Answer's JSON schema; hosted mode accepts an explicitly configured
OpenAI-compatible endpoint and JSON-object mode. The caller, not a provider,
validates JSON and checks exact citation triples. One retry includes sanitized
validation feedback without raw model input. A second failure becomes a canonical
HTTP 200 refusal, never a made-up answer or an uncaught 500. Provider failures
and refusals are not cached. Reasoning is only a brief internal evidence summary,
not requested private chain-of-thought, and is never returned in AskResponse.

The shipped local setup uses Windows Ollama, nomic-embed-text embeddings and
llama3.2:3b generation. Only those two models are required. The 3B generator is
chosen as a small instruction model capable of constrained policy responses;
no duplicate model variants or hosted subscription is required. Models are
stored in D:/Ollama/Data. WSL supplies OCR; local experiments use a measured
extraction cache and Windows inference, avoiding exposing the tray server on
all network interfaces. Generation is bounded to 512 predicted tokens with
an 8192-token context. Those bounds can yield a safe refusal if output truncates.

Only public FAST-NUCES documents are indexed. No student records or secrets
were added. Evidence is escaped and delimited, and the system prompt explicitly
labels it untrusted data. Poison instructions are ignored in stub tests and
probed during evaluation; prompt text alone is not claimed as a proof against
all attacks. Citation membership proves source attribution, not full semantic
entailment. Sensitive/confidential or personally identifying information must
not be sent to unsupported AI tools, consistent with the corpus's privacy policy.

Local operation sends generation to Ollama on this machine. Hosted operation
would send the question and retrieved public evidence to the configured third
party and must be selected intentionally. LLM_API_KEY stays in environment/K8s
Secret, is excluded from dataclass repr and logs, and is never committed.
Readiness configuration exposes model names/dimensions but no credentials.
