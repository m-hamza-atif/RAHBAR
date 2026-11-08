# ADR 0003: Chroma with one persistent server and explicit embedding pins

Status: implemented over HTTP with a Kubernetes StatefulSet and PVC.

Chroma provides explicit document embeddings, scalar metadata filters and cosine
retrieval with a small local-service footprint. The client/server version is
pinned to 1.0.12. API and indexer use environment-configured service host/port
and the same collection. Local Docker data lives in a named volume; Kubernetes
must use a StatefulSet with volumeClaimTemplates and stable service discovery.
A Deployment's replaceable pod identity is a poor default for this stateful data.
A StatefulSet alone does not provide backups, multi-writer safety or HA.

Each chunk has source, section, physical page, string doc_version and Boolean
superseded. Current retrieval excludes superseded=true; explicit historical
queries can select older editions. The indexer upserts stable IDs and removes
obsolete IDs after a complete new snapshot. Empty or partially built collections
cannot make the API ready. Collection metadata stores embed_model, embed_dim,
embedding_backend, index_revision and index_state. Matching vector length alone
does not establish matching embedding space. A model/dimension/backend conflict
returns readiness/query 503 with explicit logs; liveness stays 200.

Cosine is configured at creation. Chroma 1.0.12 rejects hnsw:space in modify(),
even unchanged; metadata updates omit that immutable key. A scaled-vector
live query confirmed distance 0.0 after updates. This was a real integration
failure discovered during Phase 2 and covered with a regression test.

SQLite/in-process vectors were simpler for isolated demos but would not prove
shared persistent service behavior across replicas. A larger managed vector
service adds deployment/account requirements unnecessary for this corpus.
A second Chroma collection for the answer cache was rejected in ADR 0002.

## StatefulSet and security implementation

`k8s/base/chroma.yaml:85` defines the 2 Gi claim mounted at `/data`, matching the
pinned server's inspected `/config.yaml`. UID/fsGroup 10001 permits volume writes
with a read-only root and bounded /tmp, without a privileged permission-fixing
init container. One standard ClusterIP `chroma` Service suffices for one HTTP
server; no extra headless Service or externally exposed data port is needed.

The actual initial rollout exposed Kubernetes injecting `CHROMA_PORT=tcp://...`.
Chroma's numeric PORT parser panicked. `enableServiceLinks: false` at
`k8s/base/chroma.yaml:84` removes that implicit configuration. Recreating the failed
pod picked up the correction while retaining its PVC. API/indexer addresses come
from explicit ConfigMap values. Default-deny policy admits only those two callers
on TCP 8000; live acceptance verifies UI denial and persistence across restart.

A StatefulSet does not provide replication, backups or method-level authorization.
Namespace RBAC must protect exec permissions and labels; a compromised API pod
still has network-level access to the Chroma HTTP endpoint. Backups and external
authentication belong to a separately approved persistent deployment.
