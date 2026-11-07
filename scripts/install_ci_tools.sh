#!/usr/bin/env bash
set -euo pipefail
# Portable installs, no sudo and no system modification. Versions are deliberate.
mkdir -p .tools
curl -fsSL https://kind.sigs.k8s.io/dl/v0.27.0/kind-linux-amd64 -o .tools/kind
curl -fsSL https://github.com/yannh/kubeconform/releases/download/v0.6.7/kubeconform-linux-amd64.tar.gz | tar -xz -C .tools kubeconform
curl -fsSL https://github.com/aquasecurity/trivy/releases/download/v0.76.2/trivy_0.76.2_Linux-64bit.tar.gz | tar -xz -C .tools trivy
curl -fsSL https://github.com/rhysd/actionlint/releases/download/v1.7.7/actionlint_1.7.7_linux_amd64.tar.gz | tar -xz -C .tools actionlint
chmod +x .tools/kind .tools/kubeconform .tools/trivy .tools/actionlint
if [[ -n "${GITHUB_PATH:-}" ]]; then echo "$PWD/.tools" >> "$GITHUB_PATH"; fi
