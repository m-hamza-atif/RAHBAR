#!/usr/bin/env bash
set -euo pipefail
# Portable installs, no sudo and no system modification. Versions are deliberate.
# CI uses the Go module proxy (or Trivy's official container), independently of
# GitHub release downloads. Local installs retain the release/API fallback.
mkdir -p .tools
scratch=$(mktemp -d)
container_id=''
cleanup() {
  if [[ -n "$container_id" ]]; then docker rm "$container_id" >/dev/null; fi
  rm -f "$scratch/download" "$scratch/metadata" "$scratch/binary" "$scratch/kind" "$scratch/kubeconform" "$scratch/actionlint"
  rmdir "$scratch"
}
trap cleanup EXIT
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
      repo=kubernetes-sigs/kind; tag=v0.27.0; asset=kind-linux-amd64; module=sigs.k8s.io/kind
      ;;
    kubeconform)
      repo=yannh/kubeconform; tag=v0.6.7; asset=kubeconform-linux-amd64.tar.gz; module=github.com/yannh/kubeconform/cmd/kubeconform
      ;;
    trivy)
      repo=aquasecurity/trivy; tag=v0.76.2; asset=trivy_0.76.2_Linux-64bit.tar.gz; module=''
      ;;
    actionlint)
      repo=rhysd/actionlint; tag=v1.7.7; asset=actionlint_1.7.7_linux_amd64.tar.gz; module=github.com/rhysd/actionlint/cmd/actionlint
      ;;
    *) echo "Unknown CI tool: $tool" >&2; exit 2 ;;
  esac
  if [[ -x ".tools/$tool" && -f ".tools/$tool.version" && $(cat ".tools/$tool.version") == "$tag" ]]; then
    echo "Using cached $tool $tag"
    continue
  fi
  if [[ "${CI_TOOL_SOURCE:-release}" == source ]]; then
    if [[ "$tool" == trivy ]]; then
      container_id=$(docker create "aquasec/trivy:${tag#v}")
      docker cp "$container_id:/usr/local/bin/trivy" "$scratch/binary"
      docker rm "$container_id" >/dev/null
      container_id=''
    else
      GOBIN="$scratch" GOPROXY=https://proxy.golang.org CGO_ENABLED=0 \
        go install -trimpath -ldflags="-s -w" "$module@$tag"
      mv "$scratch/$tool" "$scratch/binary"
    fi
  else
    release "$repo" "$tag" "$asset"
    if [[ "$tool" == kind ]]; then
      cp "$scratch/download" "$scratch/binary"
    else
      tar -xzOf "$scratch/download" "$tool" > "$scratch/binary"
    fi
  fi
  chmod +x "$scratch/binary"
  mv -f "$scratch/binary" ".tools/$tool"
  printf '%s\n' "$tag" > ".tools/$tool.version"
  echo "Installed $tool"
done
if [[ -n "${GITHUB_PATH:-}" ]]; then echo "$PWD/.tools" >> "$GITHUB_PATH"; fi
