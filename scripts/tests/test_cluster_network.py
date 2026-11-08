"""Keep the Calico pool consistent with kind before any workload receives an IP."""
import copy
import ipaddress
import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('cluster_helper', ROOT / 'scripts/cluster.py')
cluster = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cluster)


@pytest.mark.parametrize('previous', [[], [{'name': 'CALICO_IPV4POOL_CIDR', 'value': '192.168.0.0/16'}]])
def test_initial_pool_matches_kind_without_changing_other_resources(previous):
    subnet = yaml.safe_load((ROOT / 'k8s/kind.yaml').read_text())['networking']['podSubnet']
    assert ipaddress.ip_address('192.168.65.254') not in ipaddress.ip_network(subnet)
    container = {'name': 'calico-node', 'env': [{'name': 'OTHER', 'value': 'keep'}, *previous]}
    documents = [{'kind': 'ConfigMap', 'metadata': {'name': 'calico-config'}, 'data': {'keep': 'yes'}},
                 {'kind': 'DaemonSet', 'metadata': {'name': 'calico-node'},
                  'spec': {'template': {'spec': {'containers': [container]}}}}]
    unchanged = copy.deepcopy(documents[0])
    configured = cluster.configure_calico(documents, subnet)
    assert configured[0] == unchanged
    assert container['env'] == [{'name': 'OTHER', 'value': 'keep'},
                               {'name': 'CALICO_IPV4POOL_CIDR', 'value': subnet}]


def test_rejects_unsupported_ipv6_pool():
    with pytest.raises(ValueError, match='IPv4'):
        cluster.configure_calico([], 'fd00::/64')
