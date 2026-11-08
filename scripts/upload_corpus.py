"""Upload an existing public corpus to its PVC without baking documents into images."""
import argparse
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile

import yaml


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--context', required=True)
    parser.add_argument('--source', default='corpus/raw')
    parser.add_argument('--image', default='rahbar-indexer:dev')
    args = parser.parse_args()
    root = Path(args.source).resolve()
    entries = json.loads((root / '_index.json').read_text(encoding='utf-8'))
    files = ['_index.json'] + [e['file'] for e in entries]
    for name in files:
        path = root / name
        if path.resolve().parent != root or path.is_symlink() or not path.is_file():
            raise ValueError('Corpus must contain existing regular files directly inside source')
    base = ['kubectl', '--context', args.context, '-n', 'rahbar']

    def k(*parts, **kw):
        return subprocess.run([*base, *parts], check=True, **kw)

    jobs = json.loads(subprocess.check_output([*base, 'get', 'jobs', '-o', 'json']))['items']
    if any(j.get('status', {}).get('active', 0) for j in jobs):
        raise RuntimeError('Do not replace input while an indexing Job is active')
    cron = json.loads(subprocess.check_output([*base, 'get', 'cronjob', 'reindex', '-o', 'json']))
    if not cron['spec'].get('suspend'):
        raise RuntimeError('Suspend reindex before uploading; bootstrap --data-only does this')
    template = cron['spec']['jobTemplate']['spec']['template']
    container = template['spec']['containers'][0]
    container['image'] = args.image
    container['command'] = ['python', '-c', 'import time; time.sleep(1800)']
    for mount in container['volumeMounts']:
        if mount['name'] == 'corpus':
            mount['readOnly'] = False
    pod = {'apiVersion': 'v1', 'kind': 'Pod', 'metadata': {'name': 'corpus-upload',
           'namespace': 'rahbar', 'labels': {'app': 'indexer'}}, 'spec': template['spec']}
    pod['spec']['restartPolicy'] = 'Never'
    k('create', '-f', '-', input=yaml.safe_dump(pod), text=True)
    try:
        k('wait', '--for=condition=Ready', 'pod/corpus-upload', '--timeout=120s')
        with tempfile.TemporaryFile() as stream:
            with tarfile.open(fileobj=stream, mode='w') as archive:
                for name in files:
                    archive.add(root / name, arcname=name, recursive=False)
            stream.seek(0)
            k('exec', '-i', 'corpus-upload', '--', 'tar', '--no-same-owner', '-xf', '-', '-C', '/corpus', stdin=stream)
    finally:
        k('delete', 'pod', 'corpus-upload', '--wait=true')


if __name__ == '__main__':
    main()
