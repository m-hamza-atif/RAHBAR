"""Render the actual generated overlays, including the local real-model path."""
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(shutil.which('kubectl') is None, reason='kubectl required for offline Kustomize rendering')
@pytest.mark.parametrize('profile', ['dev', 'prod', 'kind'])
def test_model_overlay_renders_with_matching_config_and_scoped_egress(tmp_path, profile):
    shutil.copytree(ROOT / 'k8s', tmp_path / 'k8s', ignore=shutil.ignore_patterns('local'))
    subprocess.run([sys.executable, str(ROOT / 'scripts/configure_model.py'),
                    '--ip', '192.168.65.254', '--profile', profile], cwd=tmp_path, check=True)
    rendered = subprocess.check_output(['kubectl', 'kustomize', 'k8s/overlays/local'],
                                       cwd=tmp_path, text=True)
    docs = list(yaml.safe_load_all(rendered))
    config = next(d for d in docs if d['kind'] == 'ConfigMap')['data']
    assert config['EMBED_MODEL'] == 'nomic-embed-text' and config['EMBED_DIM'] == '768'
    assert config['LLM_PROVIDER'] == 'ollama-host' and config['CORPUS_DIR'] == '/corpus'
    assert config['CHROMA_COLLECTION'] == 'rahbar_policies'
    assert config['RELEVANCE_FLOOR'] == '0.35'
    policy = next(d for d in docs if d['kind'] == 'NetworkPolicy' and d['metadata']['name'] == 'model-egress')
    assert policy['spec']['egress'] == [{'to': [{'ipBlock': {'cidr': '192.168.65.254/32'}}],
                                        'ports': [{'protocol': 'TCP', 'port': 11434}]}]
    ingress = next(d for d in docs if d['kind'] == 'Ingress')['spec']
    assert ingress['rules'][0]['host'] == ('localhost' if profile == 'kind' else 'rahbar.local')
    assert ingress['ingressClassName'] == ('traefik' if profile == 'kind' else 'nginx')
