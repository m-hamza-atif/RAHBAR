#!/usr/bin/env bash
set -euo pipefail
# Portable installs, no sudo and no system modification. Versions are deliberate.
# Pass only the tools a job uses; no arguments preserves the local all-tools setup.
mkdir -p .tools
scratch=$(mktemp -d)
trap 'rm -f "$scratch/download" "$scratch/metadata" "$scratch/binary"; rmdir "$scratch"' EXIT
curl_options=(--fail --location --silent --show-error --retry 3 --retry-all-errors
              --retry-delay 2 --connect-timeout 15 --max-time 90 --retry-max-time 120)

release() {
  local repo=$1 tag=$2 asset=$3
  if ! curl "${curl_options[@]}" "https://github.com/$repo/releases/download/$tag/$asset" -o "$scratch/download"; then
    echo "Release download failed; trying GitHub's release API for $asset" >&2
    curl "${curl_options[@]}" "https://api.github.com/repos/$repo/releases/tags/$tag" -o "$scratch/metadata"
    local asset_url
    asset_url=$(python3 - "$scratch/metadata" "$asset" <<'PY'
import json
import sys
with open(sys.argv[1], encoding='utf-8') as source:
    assets = json.load(source)['assets']
print(next(asset['url'] for asset in assets if asset['name'] == sys.argv[2]))
PY
)
    curl "${curl_options[@]}" -H 'Accept: application/octet-stream' "$asset_url" -o "$scratch/download"
  fi
}

if [[ $# -eq 0 ]]; then set -- kind kubeconform trivy actionlint; fi
for tool in "$@"; do
  case "$tool" in
    kind)
      release kubernetes-sigs/kind v0.27.0 kind-linux-amd64
      cp "$scratch/download" "$scratch/binary"
      ;;
    kubeconform)
      release yannh/kubeconform v0.6.7 kubeconform-linux-amd64.tar.gz
      tar -xzOf "$scratch/download" kubeconform > "$scratch/binary"
      ;;
    trivy)
      release aquasecurity/trivy v0.76.2 trivy_0.76.2_Linux-64bit.tar.gz
      tar -xzOf "$scratch/download" trivy > "$scratch/binary"
      ;;
    actionlint)
      release rhysd/actionlint v1.7.7 actionlint_1.7.7_linux_amd64.tar.gz
      tar -xzOf "$scratch/download" actionlint > "$scratch/binary"
      ;;
    *) echo "Unknown CI tool: $tool" >&2; exit 2 ;;
  esac
  chmod +x "$scratch/binary"
  mv -f "$scratch/binary" ".tools/$tool"
  echo "Installed $tool"
done
if [[ -n "${GITHUB_PATH:-}" ]]; then echo "$PWD/.tools" >> "$GITHUB_PATH"; fi
