# Deployment architecture and trust boundaries

The browser crosses the HTTP Ingress boundary into static UI:8080 or API:8000.
Ingress preserves `/api/ask`; explicit readiness/health routes support external
acceptance. Three API replicas read a single Chroma HTTP server and share Redis.
They do not mount Chroma's files, fetch documents, or index during startup.
See the README Mermaid diagram and `k8s/base/services.yaml` for the four ClusterIP
Services. Only the infrastructure controller has a NodePort, bound to host loopback
by kind. External production needs TLS and authentication outside this lab scope.

Chroma 1.0.12 runs in a one-replica StatefulSet with `volumeClaimTemplates` at
`k8s/base/chroma.yaml:85`. Stable identity and a retained per-pod PVC match a single
persistent server. StatefulSet does not make Chroma highly available or provide
backups. Redis uses a Recreate Deployment with an explicit PVC and AOF/everysec;
restart persistence is useful, but an abrupt host loss can lose the last second
and a cache is not an authoritative store. Both use non-root IDs and fsGroup.
API containers use read-only images and bounded /tmp; data tiers additionally
mount their own writable `/data` volumes.

Indexer input is either packaged `/fixtures` or the read-only `/corpus` PVC.
`indexer/entrypoint.py` obtains a renewable Redis lease outside `rahbar:cache:*`,
then invokes `python -m pipeline.run`. Collection state transitions, vector pins,
snapshot revision and scoped cache invalidation remain Partner A's implementation.
The Job and CronJob container specs are identical, validated after Kustomize.
The operations script suspends scheduling and rejects active writers before manual
reindex. The Redis lease covers a scheduler/manual race; it is not a consensus
service. Do not restart Redis, clear its lease or suspend a writer host while
indexing. Lease renewal failure terminates the child before normal lease expiry.

Fixture CI still crosses real network/storage boundaries: Chroma and Redis are
real, only embeddings/generation are stubbed. The fixture collection has its own
name and baseline. Real mode needs both the public corpus and a verified model
endpoint. Default-deny egress remains closed until a local overlay adds a chosen
/32 address and TCP port for API/indexer. Hosted credentials are optional and are
never required in stub/Ollama mode.

The HPA uses autoscaling/v2, min 3/max 8 and 70% requested CPU. API CPU request is
100m. Metrics-server supplies the denominator's measurements; an accepted HPA
manifest alone does not prove a working target. I/O-bound generation needs a
future queue-depth or in-flight-request signal rather than CPU alone.

## Five concrete security holes and closures

| Hole | Closure in this implementation | Remaining boundary |
| --- | --- | --- |
| Prompt injection and fabricated model citations | Untrusted delimited evidence, strict Answer validation, one retry and exact source/section/page membership; UI uses textContent | Membership does not prove semantic entailment; real-model red teaming remains necessary |
| Compromised UI reaching vector/cache data | Calico default deny; only API/indexer allowed into Chroma/Redis; live negative tests | Kubernetes labels/RBAC must be controlled; policies do not authenticate individual HTTP methods |
| Root process, writable image or stolen pod token | Dedicated non-root UIDs, dropped ALL capabilities, no escalation, read-only roots, RuntimeDefault seccomp, no token automount | Host/CNI/Ingress infrastructure has separate privileges |
| Secrets, models or private corpus baked into image/history | Allowlisted Docker contexts; ignored raw corpus/kubeconfig/secrets; hosted-only Secret reference | Humans must protect GitHub Secrets and review publication |
| Stale cache or incompatible/partially rebuilt vectors | Single writer, revision-scoped cache, pre/post invalidation, metadata pin and Redis readiness; startup never writes | In-place rebuild intentionally creates a readiness maintenance window |

`enableServiceLinks: false` is also a runtime correctness requirement: otherwise
Kubernetes injects `CHROMA_PORT=tcp://...`, which the Rust Chroma server rejects as
non-numeric. This was discovered from real CrashLoop logs, corrected and retested.
NetworkPolicy tests require actual Calico enforcement, not kind's default network.

The kind controller is Traefik; the course minikube dev path uses its nginx addon.
Ingress-NGINX maintenance ended in March 2026; do not deploy that retired controller
to an external production environment. See the linked official notice in README.
