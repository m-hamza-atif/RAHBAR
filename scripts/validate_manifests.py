"""Validate rendered manifests, not text patterns or unexpanded Kustomize patches."""
import argparse
import subprocess
from pathlib import Path

import yaml


def validate(docs, profile):
    by = {(d['kind'], d['metadata']['name']): d for d in docs}
    assert len(by) == len(docs), 'duplicate resource identity'
    assert ('Namespace', 'rahbar') in by
    assert all(d['metadata'].get('namespace') == 'rahbar'
               for d in docs if d['kind'] != 'Namespace')
    services = [d for d in docs if d['kind'] == 'Service']
    assert {d['metadata']['name'] for d in services} == {'api', 'ui', 'chroma', 'redis'}
    assert all(d['spec']['type'] == 'ClusterIP' for d in services)
    assert not any(d['kind'] == 'Secret' for d in docs), 'Never apply placeholder Secrets'
    ingress_paths = by['Ingress', 'rahbar']['spec']['rules'][0]['http']['paths']
    routes = {p['path']: p['backend']['service']['name'] for p in ingress_paths}
    assert routes == {'/': 'ui', '/api': 'api', '/readyz': 'api', '/healthz': 'api'}
    assert all(p['pathType'] == 'Prefix' for p in ingress_paths)
    for name in ('api', 'ui', 'indexer', 'chroma', 'redis'):
        assert by['ServiceAccount', name]['automountServiceAccountToken'] is False
    for d in docs:
        if d['kind'] not in ('Deployment', 'StatefulSet', 'Job', 'CronJob'):
            continue
        template = (d['spec']['jobTemplate']['spec']['template'] if d['kind'] == 'CronJob'
                    else d['spec']['template'])
        spec = template['spec']
        assert spec['automountServiceAccountToken'] is False
        assert spec['enableServiceLinks'] is False, 'Chroma service links collide with its PORT config'
        assert spec['securityContext']['runAsNonRoot'] is True
        assert spec['securityContext']['seccompProfile']['type'] == 'RuntimeDefault'
        for c in spec['containers']:
            assert ':' in c['image'] and not c['image'].endswith(':latest')
            security = c['securityContext']
            assert security['readOnlyRootFilesystem'] is True
            assert security['allowPrivilegeEscalation'] is False
            assert security['capabilities']['drop'] == ['ALL']
            assert all(c['resources'][bound].get(key) for bound in ('requests', 'limits')
                       for key in ('cpu', 'memory'))
            assert not any('secretRef' in e for e in c.get('envFrom', []))
    api = by['Deployment', 'api']['spec']
    assert api['replicas'] == 3
    assert api['strategy']['rollingUpdate'] == {'maxSurge': 1, 'maxUnavailable': 0}
    assert api['template']['spec']['terminationGracePeriodSeconds'] == 30
    c = api['template']['spec']['containers'][0]
    assert c['startupProbe']['httpGet']['path'] == '/healthz'
    assert (c['startupProbe']['failureThreshold'], c['startupProbe']['periodSeconds']) == (30, 2)
    assert c['livenessProbe']['httpGet']['path'] == '/healthz'
    assert c['readinessProbe']['httpGet']['path'] == '/readyz'
    assert c['livenessProbe']['periodSeconds'] == 20
    assert c['readinessProbe']['periodSeconds'] == 10
    assert 'preStop' in c['lifecycle']
    hpa = by['HorizontalPodAutoscaler', 'api']
    assert hpa['apiVersion'] == 'autoscaling/v2'
    assert (hpa['spec']['minReplicas'], hpa['spec']['maxReplicas']) == (3, 8)
    assert hpa['spec']['metrics'][0]['resource']['target']['averageUtilization'] == 70
    job = by['Job', 'indexer']['spec']
    cron = by['CronJob', 'reindex']['spec']
    assert job == cron['jobTemplate']['spec'], 'Job and CronJob must share exact writer configuration'
    assert job['template']['spec']['restartPolicy'] == 'OnFailure'
    assert job['backoffLimit'] == 3 and cron['concurrencyPolicy'] == 'Forbid'
    assert cron['schedule'] == '0 2 * * 0'
    assert by['StatefulSet', 'chroma']['spec']['volumeClaimTemplates']
    assert ('PersistentVolumeClaim', 'redis-data') in by
    deny = by['NetworkPolicy', 'default-deny']['spec']
    assert deny['podSelector'] == {} and deny['ingress'] == [] and deny['egress'] == []
    assert set(deny['policyTypes']) == {'Ingress', 'Egress'}
    for name in ('api', 'indexer'):
        destinations = by['NetworkPolicy', name+'-data']['spec']['egress']
        assert {r['to'][0]['podSelector']['matchLabels']['app'] for r in destinations} == {'chroma', 'redis'}
    conf = by['ConfigMap', 'rahbar-config']['data']
    assert conf['RETRIEVER'] == 'chroma' and conf['REDIS_FAKE'] == 'false'
    assert conf['CHUNK_SIZE'] == '512' and conf['CHUNK_OVERLAP'] == '64'
    if profile == 'ci':
        for key, value in {'EMBED_MODEL': 'stub', 'EMBED_DIM': '384', 'LLM_PROVIDER': 'stub',
                           'CORPUS_DIR': '/fixtures', 'RELEVANCE_FLOOR': '0.15'}.items():
            assert conf[key] == value, key
    else:
        assert conf['EMBED_MODEL'] == 'nomic-embed-text' and conf['EMBED_DIM'] == '768'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kubeconform', default='kubeconform')
    args = parser.parse_args()
    Path('.artifacts').mkdir(exist_ok=True)
    for profile in ('base', 'dev', 'prod', 'ci'):
        path = 'k8s/base' if profile == 'base' else 'k8s/overlays/'+profile
        rendered = subprocess.check_output(['kubectl', 'kustomize', path], text=True, encoding='utf-8')
        validate(list(yaml.safe_load_all(rendered)), profile)
        output = Path('.artifacts') / (profile+'.yaml')
        output.write_text(rendered, encoding='utf-8')
        subprocess.run([args.kubeconform, '-strict', '-summary', '-kubernetes-version',
                        '1.32.0', str(output)], check=True)
        print(profile+': invariants and strict schema PASS')


if __name__ == '__main__':
    main()
