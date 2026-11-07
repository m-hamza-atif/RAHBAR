"""Ordered bootstrap/reindex. All kubectl calls require an explicit context."""
import argparse
import copy
import json
import subprocess
import time

import yaml


def command(args, **kwargs):
    return subprocess.run(args, check=True, text=True, encoding='utf-8', **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--context', required=True)
    parser.add_argument('--overlay', default='k8s/overlays/ci')
    parser.add_argument('--reindex', action='store_true')
    parser.add_argument('--data-only', action='store_true', help='prepare PVCs/data services before uploading a real corpus')
    parser.add_argument('--image-prefix', default='')
    parser.add_argument('--tag', default='dev')
    args = parser.parse_args()
    kubectl = ['kubectl', '--context', args.context]

    def k(*parts, **kwargs):
        return command([*kubectl, *parts], **kwargs)

    def apply(items):
        if items:
            k('apply', '-f', '-', input=yaml.safe_dump_all(items))

    def get(kind, name=None):
        parts = ['get', kind, '-n', 'rahbar'] + ([name] if name else [])
        return json.loads(k(*parts, '-o', 'json', capture_output=True).stdout)

    docs = list(yaml.safe_load_all(command(
        ['kubectl', 'kustomize', args.overlay], capture_output=True).stdout))
    for doc in docs:
        kind = doc['kind']
        if kind in ('Deployment', 'StatefulSet', 'Job', 'CronJob'):
            template = (doc['spec']['jobTemplate']['spec']['template'] if kind == 'CronJob'
                        else doc['spec']['template'])
            for container in template['spec']['containers']:
                if container['image'].startswith('rahbar-'):
                    container['image'] = f"{args.image_prefix}{container['image'].split(':')[0]}:{args.tag}"
    desired_cron = next(d for d in docs if d['kind'] == 'CronJob')
    job = next(d for d in docs if d['kind'] == 'Job')
    if args.reindex:
        original = get('cronjob', 'reindex')['spec'].get('suspend', False)
        k('patch', 'cronjob', 'reindex', '-n', 'rahbar', '--type=merge',
          '-p', json.dumps({'spec': {'suspend': True}}))
        # Forbid only serializes this CronJob. Check *all* active indexer Jobs,
        # and the image wrapper's Redis lease closes the remaining scheduling race.
        jobs = get('jobs')['items']
        active = [j['metadata']['name'] for j in jobs
                  if j['spec']['template']['metadata'].get('labels', {}).get('app') == 'indexer'
                  and not any(c['type'] in ('Complete', 'Failed') and c['status'] == 'True'
                              for c in j.get('status', {}).get('conditions', []))]
        if active:
            raise RuntimeError(f'Active indexing Jobs: {active}; schedule left suspended')
        # Create from the applied template, so reindex cannot silently use stale dev images.
        cron = get('cronjob', 'reindex')
        job = {'apiVersion': 'batch/v1', 'kind': 'Job',
               'metadata': {'name': f'reindex-{time.time_ns()}', 'namespace': 'rahbar'},
               'spec': cron['spec']['jobTemplate']['spec']}
        apply([job])
        k('wait', '--for=condition=complete', 'job/'+job['metadata']['name'],
          '-n', 'rahbar', '--timeout=1800s')
        k('patch', 'cronjob', 'reindex', '-n', 'rahbar', '--type=merge',
          '-p', json.dumps({'spec': {'suspend': original}}))
    else:
        apply([d for d in docs if d['kind'] == 'Namespace'])
        infrastructure = [d for d in docs if d['kind'] not in
                          ('Namespace', 'Job', 'CronJob', 'HorizontalPodAutoscaler', 'Ingress')
                          and not (d['kind'] == 'Deployment' and d['metadata']['name'] in ('api', 'ui'))]
        apply(infrastructure)
        suspended = copy.deepcopy(desired_cron)
        suspended['spec']['suspend'] = True
        apply([suspended])
        for resource in ('statefulset/chroma', 'deployment/redis'):
            k('rollout', 'status', resource, '-n', 'rahbar', '--timeout=300s')
        if args.data_only:
            print('Data services ready; schedule suspended. Upload corpus before full bootstrap.')
            return
        existing = get('jobs')['items']
        old = next((j for j in existing if j['metadata']['name'] == 'indexer'), None)
        if old is None:
            apply([job])
        elif old.get('status', {}).get('failed', 0):
            raise RuntimeError('Existing bootstrap Job failed; inspect it, then use --reindex. No automatic deletion.')
        k('wait', '--for=condition=complete', 'job/indexer', '-n', 'rahbar', '--timeout=1800s')
        apply([d for d in docs if (d['kind'] == 'Deployment' and d['metadata']['name'] in ('api', 'ui'))
               or d['kind'] in ('HorizontalPodAutoscaler', 'Ingress')])
        apply([desired_cron])
    for name in ('api', 'ui'):
        k('rollout', 'status', 'deployment/'+name, '-n', 'rahbar', '--timeout=300s')
    if get('deployment', 'api').get('status', {}).get('readyReplicas', 0) < 3:
        raise RuntimeError('Fewer than three ready API replicas')
    print('Ordered deployment complete; run ingress evaluation and acceptance next.')


if __name__ == '__main__':
    main()
