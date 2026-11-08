"""Live fixture acceptance. Mutations are confined to the explicitly named context."""
import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

import httpx
import yaml


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--context', required=True)
    parser.add_argument('--api', default='http://127.0.0.1:18080')
    args = parser.parse_args()
    records = []
    Path('.artifacts').mkdir(exist_ok=True)

    def record(name, detail):
        records.append({'time': datetime.now(timezone.utc).isoformat(), 'check': name,
                        'status': 'PASS', 'detail': detail})
        print(name+': PASS', flush=True)

    def k(*parts, check=True, **kw):
        result = subprocess.run(['kubectl', '--context', args.context, '-n', 'rahbar', *parts],
                                capture_output=True, text=True, encoding='utf-8', **kw)
        if check and result.returncode:
            raise RuntimeError(' '.join(parts)+'\n'+result.stdout+result.stderr)
        return result

    def get(kind, name):
        return json.loads(k('get', kind, name, '-o', 'json').stdout)

    client = httpx.Client(base_url=args.api, headers={'Host': 'rahbar.local'}, timeout=30)

    def ready():
        response = client.get('/readyz')
        response.raise_for_status()
        if 'application/json' not in response.headers.get('content-type', ''):
            raise RuntimeError('Ingress /readyz returned non-JSON content')
        data = response.json()
        if data.get('status') != 'ready':
            raise RuntimeError('API not ready: ' + str(data))
        return data

    def ask():
        response = client.post('/api/ask', json={'question': 'When is a student placed on academic warning?'})
        response.raise_for_status()
        return response.json()

    def wait_ready():
        for _ in range(60):
            try:
                return ready()
            except (httpx.HTTPError, json.JSONDecodeError, KeyError, RuntimeError):
                time.sleep(2)
        raise RuntimeError('Ingress did not recover')

    try:
        state = ready()
        assert state['configuration']['retriever'] == 'chroma'
        assert state['configuration']['embed_model'] == 'stub'
        assert state['configuration']['llm_provider'] == 'stub'
        assert client.get('/').status_code == 200
        first, second = ask(), ask()
        assert first['answered_from_context'] and first['citations'] and second['cached']
        record('ingress-ui-api-cache', second)
        endpoints = get('endpoints', 'api')
        addresses = [a for subset in endpoints['subsets'] for a in subset.get('addresses', [])]
        assert len(addresses) >= 3
        record('three-ready-endpoints', addresses)
        for resource in ('api', 'ui', 'chroma', 'redis'):
            assert get('service', resource)['spec']['type'] == 'ClusterIP'
        record('private-data-services', 'all four application/data services are ClusterIP')
        code = "import socket; print(socket.gethostbyname('redis')); s=socket.create_connection(('redis',6379),3); s.close(); s=socket.create_connection(('chroma',8000),3); s.close()"
        result = k('exec', 'deployment/api', '--', 'python', '-c', code)
        record('api-dns-data-access', result.stdout)
        result = k('exec', 'deployment/ui', '--', 'nslookup', '-type=A', 'chroma.rahbar.svc.cluster.local')
        record('ui-dns', result.stdout)
        for host, port in [('chroma', 8000), ('redis', 6379)]:
            result = k('exec', 'deployment/ui', '--', 'wget', '-T', '3', '-O', '-',
                       f'http://{host}:{port}', check=False)
            assert result.returncode != 0 and 'timed out' in result.stderr.lower(), result.stderr
            record('ui-denied-'+host, result.stderr)
        # Persisted revision and cached answer must survive data-process replacement.
        revision = state['index_revision']
        k('delete', 'pod', 'chroma-0', '--wait=true')
        k('rollout', 'status', 'statefulset/chroma', '--timeout=180s')
        assert wait_ready()['index_revision'] == revision
        record('chroma-pvc-restart', revision)
        k('rollout', 'restart', 'deployment/redis')
        k('rollout', 'status', 'deployment/redis', '--timeout=180s')
        wait_ready()
        assert ask()['cached']
        record('redis-aof-restart', 'cached answer survived Redis restart')
        subprocess.run([sys.executable, 'scripts/deploy.py', '--context', args.context, '--reindex'], check=True)
        new = wait_ready()['index_revision']
        assert new != revision and not ask()['cached']
        record('reindex-revision-cache-invalidation', {'before': revision, 'after': new})
        count_code = "import chromadb; from chromadb.config import Settings; import os; c=chromadb.HttpClient(host='chroma',port=8000,settings=Settings(anonymized_telemetry=False)); print(c.get_collection(os.environ['CHROMA_COLLECTION']).count())"
        count = int(k('exec', 'deployment/api', '--', 'python', '-c', count_code).stdout.strip())
        assert count > 0
        subprocess.run([sys.executable, 'scripts/deploy.py', '--context', args.context, '--reindex'], check=True)
        wait_ready()
        assert int(k('exec', 'deployment/api', '--', 'python', '-c', count_code).stdout.strip()) == count
        record('repeat-index-idempotent-count', count)
        # An isolated API replica has a wrong pin; readiness excludes it from Service.
        template = copy.deepcopy(get('deployment', 'api')['spec']['template'])
        pod = {'apiVersion': 'v1', 'kind': 'Pod', 'metadata': {'name': 'api-pin-test',
               'namespace': 'rahbar', 'labels': template['metadata']['labels']}, 'spec': template['spec']}
        pod['spec']['containers'][0]['env'].append({'name': 'EMBED_MODEL', 'value': 'deliberate-mismatch'})
        k('create', '-f', '-', input=yaml.safe_dump(pod))
        try:
            k('wait', '--for=jsonpath={.status.phase}=Running', 'pod/api-pin-test', '--timeout=120s')
            code = "import httpx,time; time.sleep(3); a=httpx.get('http://127.0.0.1:8000/healthz'); b=httpx.get('http://127.0.0.1:8000/readyz'); print(a.status_code,b.status_code,b.text); assert a.status_code==200 and b.status_code==503"
            result = k('exec', 'api-pin-test', '--', 'python', '-c', code)
            record('pin-mismatch-fail-closed', result.stdout+k('logs', 'api-pin-test').stdout)
        finally:
            k('delete', 'pod', 'api-pin-test', '--wait=true')
        for _ in range(60):
            hpa = get('hpa', 'api')
            metrics = hpa.get('status', {}).get('currentMetrics', [])
            if any('averageUtilization' in m.get('resource', {}).get('current', {}) for m in metrics):
                record('hpa-numeric-target', hpa['status'])
                break
            time.sleep(2)
        else:
            raise RuntimeError('HPA CPU remains unknown')
        patch = {'spec': {'template': {'metadata': {'annotations': {'rahbar.io/rollout-proof': str(time.time_ns())}}}}}
        k('patch', 'deployment', 'api', '--type=merge', '-p', json.dumps(patch))
        k('rollout', 'status', 'deployment/api', '--timeout=180s')
        ask()
        k('rollout', 'undo', 'deployment/api')
        k('rollout', 'status', 'deployment/api', '--timeout=180s')
        ask()
        record('rollout-rollback-recovered', k('rollout', 'history', 'deployment/api').stdout)
        record('kubectl-top-snapshot', k('top', 'pods').stdout)
    except Exception as exc:
        records.append({'time': datetime.now(timezone.utc).isoformat(), 'status': 'FAIL', 'detail': str(exc)})
        raise
    finally:
        Path('.artifacts/acceptance.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
        client.close()


if __name__ == '__main__':
    main()
