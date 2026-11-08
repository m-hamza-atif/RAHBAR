"""Create an ignored real-model overlay with narrowly scoped host egress."""
import argparse
import ipaddress
from pathlib import Path

import yaml


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ip', required=True, help='verified trusted reachable IPv4 model host')
    parser.add_argument('--port', type=int, default=11434)
    parser.add_argument('--profile', choices=['dev', 'prod'], default='dev')
    args = parser.parse_args()
    address = ipaddress.IPv4Address(args.ip)
    if address.is_unspecified or address.is_loopback or address.is_multicast:
        raise ValueError('Supply an actual cluster-reachable host, not loopback/wildcard')
    if not 1 <= args.port <= 65535:
        raise ValueError('Invalid port')
    target = Path('k8s/overlays/local')
    target.mkdir(exist_ok=True)
    policy = {'apiVersion': 'networking.k8s.io/v1', 'kind': 'NetworkPolicy',
              'metadata': {'name': 'model-egress', 'namespace': 'rahbar'},
              'spec': {'podSelector': {'matchExpressions': [{'key': 'app', 'operator': 'In',
                                                           'values': ['api', 'indexer']}]},
                       'policyTypes': ['Egress'], 'egress': [{'to': [{'ipBlock': {'cidr': f'{address}/32'}}],
                                    'ports': [{'protocol': 'TCP', 'port': args.port}]}]}}
    (target / 'model-egress.yaml').write_text(yaml.safe_dump(policy, sort_keys=False), encoding='utf-8')
    patch = {'apiVersion': 'v1', 'kind': 'ConfigMap',
             'metadata': {'name': 'rahbar-config', 'namespace': 'rahbar'},
             'data': {'OLLAMA_BASE_URL': f'http://{address}:{args.port}'}}
    kustomization = {'apiVersion': 'kustomize.config.k8s.io/v1beta1', 'kind': 'Kustomization',
                     'resources': [f'../{args.profile}', 'model-egress.yaml'],
                     'patches': [{'patch': yaml.safe_dump(patch, sort_keys=False)}]}
    (target / 'kustomization.yaml').write_text(yaml.safe_dump(kustomization, sort_keys=False), encoding='utf-8')
    print('Created ignored k8s/overlays/local; verify model host/firewall before deployment.')


if __name__ == '__main__':
    main()
