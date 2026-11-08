"""Capture real diagnostics; failed commands are recorded as failures, never passes."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--context', required=True)
    parser.add_argument('--out', default='.artifacts/diagnostics.txt')
    args = parser.parse_args()
    commands = [
        ['get', 'pods', '-o', 'wide'], ['get', 'endpoints', 'api'],
        ['get', 'endpointslices', '-l', 'kubernetes.io/service-name=api', '-o', 'yaml'],
        ['get', 'hpa'], ['top', 'pods'], ['get', 'jobs'], ['get', 'pvc'],
        ['get', 'events', '--sort-by=.lastTimestamp'], ['describe', 'pods'],
        ['logs', '-l', 'app=indexer', '--all-containers=true', '--tail=100'],
        ['logs', '-l', 'app=api', '--all-containers=true', '--tail=100'],
    ]
    output = [f'Captured {datetime.now(timezone.utc).isoformat()} context={args.context}']
    for parts in commands:
        cmd = ['kubectl', '--context', args.context, '-n', 'rahbar', *parts]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        output.extend(['\n$ '+' '.join(cmd), f'exit={result.returncode}', result.stdout, result.stderr])
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(output), encoding='utf-8')


if __name__ == '__main__':
    main()
