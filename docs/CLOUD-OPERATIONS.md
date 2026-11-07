# Release and cloud operations

The automated CD environment is an ephemeral kind cluster on a GitHub runner.
It deploys published SHA-tagged images in the fixture profile with real Chroma and
Redis. It is not a persistent cloud service and makes no claim of live FAST/Ollama
availability. Persistent cloud deployment requires a selected account, region,
cluster context, storage class, DNS/TLS, model host and explicit spending approval;
none is provisioned or billed by this repository's local workflow.

## Human release configuration

1. In repository Settings -> Secrets and variables -> Actions, create
   DOCKERHUB_USERNAME and a scoped DOCKERHUB_TOKEN. Create/authorize the three
   repositories `rahbar-api`, `rahbar-indexer`, `rahbar-ui` under that account.
2. Protect `main`: require a pull request, one approval, green CI jobs lint, test,
   manifests, build, scan and e2e-eval, and block direct pushes. Select the actual
   check names after the first workflow runs; do not invent remote run links.
3. Review and manually commit/push `dev`; open `dev -> main`. Capture branch
   protection and a genuine blocked merge from an isolated failed-evaluation test,
   then restore it and capture the green checks. Never change frozen baselines.
4. After human approval and merge, inspect CD. Its test stage gates build-push;
   scan gates publication; deploy pulls the exact github.sha tags. Record the
   actual Actions run and Docker Hub image URLs/digests.

CI builds do not authenticate to or push a registry. Images travel between runners
through an explicit saved-image artifact. Linux/amd64 export avoids incomplete
multi-platform references in Docker Desktop's containerd image store. Artifacts
contain no kubeconfig, models or downloaded PDFs. Failed gate logs remain failed.

## Hosted-only Secret creation

Stub and Ollama do not need `rahbar-secret`. The committed placeholder is never
included in Kustomize. For hosted mode, read the key with Python getpass and send
a Secret directly to kubectl stdin (no file, shell-history value or command-line
credential). From the repository's Python environment, a human can run:

```python
import getpass, json, subprocess
context = input('Explicit Kubernetes context: ')
key = getpass.getpass('Hosted LLM key: ')
secret = {'apiVersion': 'v1', 'kind': 'Secret',
          'metadata': {'name': 'rahbar-secret', 'namespace': 'rahbar'},
          'type': 'Opaque', 'stringData': {'LLM_API_KEY': key}}
subprocess.run(['kubectl', '--context', context, 'apply', '-f', '-'],
               input=json.dumps(secret), text=True, check=True)
```

Add `env: [{name: LLM_API_KEY, valueFrom: {secretKeyRef: {name: rahbar-secret,
key: LLM_API_KEY}}}]` to the API only in an ignored hosted overlay; set provider,
base URL including the version path, and model name. The matching embedding host
still needs explicit egress. Use your network's controlled proxy/IP policy for a
changing hosted-provider address; do not add unrestricted 0.0.0.0/0 egress.

## Persistent cloud adaptation and rollback

Before applying prod, supply exact SHA image names via `scripts/deploy.py`'s
`--image-prefix account/ --tag SHA`, a supported Ingress controller and namespace
selectors, approved storage class and trusted model endpoint. Render and strictly
validate the resulting overlay. Upload the public corpus to its PVC before the
bootstrap Job. Configure backups outside the application: Chroma StatefulSet and
Redis PVCs survive pod replacement, not storage loss or cluster deletion.

Rollback API/UI through Deployment revisions only after checking index/model
compatibility. A rollback cannot convert vector spaces. Preserve original corpus
and compatible image/config versions for reindex recovery. Readiness protects
traffic during an incompatible configuration, while liveness preserves processes.
Monitor API latency, refusals, fallback count, cache ratio, Job failures, PVC space
and HPA availability. CPU is a weak generation-load signal; consider concurrency
or queue-depth scaling through an adapter/KEDA in a later measured design.

Remote secrets, branch protection, PR review, screenshots, publication and genuine
remote URLs remain human responsibilities; local files cannot prove them complete.
