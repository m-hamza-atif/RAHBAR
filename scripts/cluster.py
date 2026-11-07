"""Create a dedicated fixture cluster without changing the user's kubeconfig."""
import argparse
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default='rahbar-b')
    parser.add_argument('--kubeconfig', default='.artifacts/kubeconfig')
    parser.add_argument('--existing', action='store_true', help='configure an already-created dedicated cluster')
    args = parser.parse_args()
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
    # Calico is required: kindnet alone does not prove NetworkPolicy enforcement.
    k('apply', '-f', 'https://raw.githubusercontent.com/projectcalico/calico/v3.29.3/manifests/calico.yaml')
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
