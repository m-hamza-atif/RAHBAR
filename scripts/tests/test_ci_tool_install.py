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
               CI_TOOL_SOURCE='release',
               TEST_MODE=mode, PAYLOAD=str(archive), CALL_LOG=str(log),
               GITHUB_PATH=str(tmp_path / 'github-path'))
    result = subprocess.run(['bash', str(INSTALLER), 'kubeconform'], cwd=tmp_path,
                            env=env, capture_output=True, text=True)
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert all('--retry-all-errors' in args for args in calls)
    if mode == 'failed':
        assert set(p.name for p in tools.iterdir()) == {'kubeconform'}
        assert result.returncode != 0
        assert target.read_bytes() == b'previous-working-version'
    else:
        assert set(p.name for p in tools.iterdir()) == {'kubeconform', 'kubeconform.version'}
        assert result.returncode == 0, result.stderr
        assert target.read_bytes() == binary and os.access(target, os.X_OK)
        assert (tmp_path / 'github-path').read_text().strip() == str(tools)
        assert len(calls) == (3 if mode == 'fallback' else 1)
        before = log.read_text()
        cached = subprocess.run(['bash', str(INSTALLER), 'kubeconform'], cwd=tmp_path,
                                env=dict(env, TEST_MODE='failed'), capture_output=True, text=True)
        assert cached.returncode == 0 and log.read_text() == before


@pytest.mark.parametrize('tool,fail', [('kubeconform', False), ('actionlint', False),
                                     ('kind', False), ('trivy', False), ('kubeconform', True)])
def test_ci_source_install_avoids_release_servers(tmp_path, tool, fail):
    fake_bin = tmp_path / 'bin'
    fake_bin.mkdir()
    fake = '''#!/usr/bin/env python3
import os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
if name == 'curl':
    raise AssertionError('CI must not use release downloads')
if os.environ['FAIL_BUILD'] == 'yes':
    sys.exit(1)
if name == 'go':
    assert os.environ['GOPROXY'] == 'https://proxy.golang.org'
    assert '@v' in sys.argv[-1]
    (pathlib.Path(os.environ['GOBIN']) / os.environ['TOOL']).write_text('verified source binary')
elif sys.argv[1] == 'create':
    assert sys.argv[2] == 'aquasec/trivy:0.76.2'
    print('test-container')
elif sys.argv[1] == 'cp':
    pathlib.Path(sys.argv[3]).write_text('verified source binary')
'''
    for name in ('curl', 'go', 'docker'):
        path = fake_bin / name
        path.write_text(fake)
        path.chmod(0o755)
    tools = tmp_path / '.tools'
    tools.mkdir()
    target = tools / tool
    target.write_text('previous binary')
    env = dict(os.environ, PATH=str(fake_bin)+os.pathsep+os.environ['PATH'],
               CI_TOOL_SOURCE='source', TOOL=tool, FAIL_BUILD='yes' if fail else 'no')
    result = subprocess.run(['bash', str(INSTALLER), tool], cwd=tmp_path,
                            env=env, capture_output=True, text=True)
    assert (result.returncode != 0) == fail, result.stderr
    assert target.read_text() == ('previous binary' if fail else 'verified source binary')
