"""Exercise release recovery without relying on the public download servers."""
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile

import pytest

pytestmark = pytest.mark.skipif(os.name == 'nt', reason='CI installer runs under Linux/bash')
INSTALLER = Path(__file__).resolve().parents[1] / 'install_ci_tools.sh'


@pytest.mark.parametrize('mode', ['direct', 'fallback', 'failed'])
def test_requested_tool_recovers_or_preserves_existing_binary(tmp_path, mode):
    binary = b'#!/bin/sh\necho verified-tool\n'
    archive = tmp_path / 'payload.tar.gz'
    with tarfile.open(archive, 'w:gz') as bundle:
        entry = tarfile.TarInfo('kubeconform')
        entry.size = len(binary)
        bundle.addfile(entry, io.BytesIO(binary))
    fake_bin = tmp_path / 'bin'
    fake_bin.mkdir()
    curl = fake_bin / 'curl'
    curl.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
args = sys.argv[1:]
url = next(a for a in args if a.startswith('https://'))
destination = pathlib.Path(args[args.index('-o')+1])
with open(os.environ['CALL_LOG'], 'a') as log:
    log.write(json.dumps(args)+'\\n')
if os.environ['TEST_MODE'] == 'failed' or (
    os.environ['TEST_MODE'] == 'fallback' and 'github.com/' in url and 'api.github.com' not in url):
    destination.write_bytes(b'partial')
    sys.exit(22)
if '/releases/tags/' in url:
    destination.write_text(json.dumps({'assets': [{'name': 'kubeconform-linux-amd64.tar.gz',
        'url': 'https://api.github.com/repos/test/releases/assets/123'}]}))
else:
    destination.write_bytes(pathlib.Path(os.environ['PAYLOAD']).read_bytes())
''')
    curl.chmod(0o755)
    tools = tmp_path / '.tools'
    tools.mkdir()
    target = tools / 'kubeconform'
    target.write_bytes(b'previous-working-version')
    log = tmp_path / 'calls.jsonl'
    env = dict(os.environ, PATH=str(fake_bin)+os.pathsep+os.environ['PATH'],
               TEST_MODE=mode, PAYLOAD=str(archive), CALL_LOG=str(log),
               GITHUB_PATH=str(tmp_path / 'github-path'))
    result = subprocess.run(['bash', str(INSTALLER), 'kubeconform'], cwd=tmp_path,
                            env=env, capture_output=True, text=True)
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert all('--retry-all-errors' in args for args in calls)
    assert set(p.name for p in tools.iterdir()) == {'kubeconform'}
    if mode == 'failed':
        assert result.returncode != 0
        assert target.read_bytes() == b'previous-working-version'
    else:
        assert result.returncode == 0, result.stderr
        assert target.read_bytes() == binary and os.access(target, os.X_OK)
        assert (tmp_path / 'github-path').read_text().strip() == str(tools)
        assert len(calls) == (3 if mode == 'fallback' else 1)
