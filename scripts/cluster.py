"""Create a dedicated fixture cluster without changing the user's kubeconfig."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import subprocess
from urllib.request import urlopen

import yaml


def configure_calico(documents, pod_subnet):
    """Set the initial Calico pool before its first pod can create a default pool."""
    documents = [d for d in documents if d]
    network = ipaddress.ip_network(pod_subnet)
    if network.version != 4:
        raise ValueError('This cluster helper requires an IPv4 pod subnet')
    daemon = next(d for d in documents if d.get('kind') == 'DaemonSet'
                  and d['metadata']['name'] == 'calico-node')
    container = next(c for c in daemon['spec']['template']['spec']['containers']
                     if c['name'] == 'calico-node')
    env = container.setdefault('env', [])
    env[:] = [e for e in env if e['name'] != 'CALICO_IPV4POOL_CIDR']
    env.append({'name': 'CALICO_IPV4POOL_CIDR', 'value': str(network)})
    return documents


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default='rahbar-b')
    parser.add_argument('--kubeconfig', default='.artifacts/kubeconfig')
    parser.add_argument('--existing', action='store_true', help='configure an already-created dedicated cluster')
    args = parser.parse_args()
    pod_subnet = yaml.safe_load(Path('k8s/kind.yaml').read_text())['networking']['podSubnet']
    config = Path(args.kubeconfig).resolve()
    config.parent.mkdir(exist_ok=True)
    os.environ['KUBECONFIG'] = str(config)
    context = 'kind-'+args.name

    def run(*parts):
        subprocess.run(parts, check=True)

    def k(*parts):
        run('kubectl', '--context', context, *parts)

    if not args.existing:
        run('kind', 'create', 'cluster', '--name', args.name, '--image', 'kindest/node:v1.32.2',
            '--config', 'k8s/kind.yaml', '--kubeconfig', str(config))
    # Refuse to reinterpret an older cluster's addresses with a new default range.
    nodes = json.loads(subprocess.check_output(
        ['kubectl', '--context', context, 'get', 'nodes', '-o', 'json'], text=True))
    if any(not ipaddress.ip_network(n['spec']['podCIDR']).subnet_of(ipaddress.ip_network(pod_subnet))
           for n in nodes['items'] if n['spec'].get('podCIDR')):
        raise RuntimeError('Existing cluster pod CIDR differs from k8s/kind.yaml; use a new dedicated cluster name')
    # Calico is required: kindnet alone does not prove NetworkPolicy enforcement.
    # Patch the pinned manifest before apply: patching a running DaemonSet races
    # creation of its default pool and can leave pods in the wrong address space.
    url = 'https://raw.githubusercontent.com/projectcalico/calico/v3.29.3/manifests/calico.yaml'
    with urlopen(url, timeout=60) as response:
        calico = configure_calico(list(yaml.safe_load_all(response.read())), pod_subnet)
    subprocess.run(['kubectl', '--context', context, 'apply', '-f', '-'],
                   input=yaml.safe_dump_all(calico), text=True, check=True)
    k('rollout', 'status', 'daemonset/calico-node', '-n', 'kube-system', '--timeout=300s')
    k('wait', '--for=condition=Ready', 'nodes', '--all', '--timeout=300s')
    k('apply', '-f', 'https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.7.2/components.yaml')
    # kind kubelets use self-signed serving certificates; this exception is limited
    # to this disposable lab cluster, not an application or production setting.
    k('patch', 'deployment', 'metrics-server', '-n', 'kube-system', '--type=json', '-p',
      '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]')
    k('rollout', 'status', 'deployment/metrics-server', '-n', 'kube-system', '--timeout=300s')
    k('apply', '-f', 'k8s/infra/traefik.yaml')
    k('rollout', 'status', 'deployment/traefik', '-n', 'ingress-system', '--timeout=300s')
    print(f'Use KUBECONFIG={config} and explicit --context {context}')


if __name__ == '__main__':
    main()
