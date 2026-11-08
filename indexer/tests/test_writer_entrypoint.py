"""The container lease must reject overlap and stop writing on renewal failure."""
import importlib.util
from pathlib import Path
import subprocess
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def wrapper(monkeypatch):
    path = Path(__file__).resolve().parents[1] / 'entrypoint.py'
    spec = importlib.util.spec_from_file_location('writer_entrypoint', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.signal, 'signal', lambda *args: None)
    monkeypatch.setattr(module.sys, 'argv', ['entrypoint.py'])
    client = MagicMock()
    monkeypatch.setattr(module.redis.Redis, 'from_url', lambda *args, **kwargs: client)
    process = MagicMock()
    spawn = MagicMock(return_value=process)
    monkeypatch.setattr(module.subprocess, 'Popen', spawn)
    return module, client.lock.return_value, process, spawn


def test_existing_writer_prevents_pipeline_start(wrapper):
    module, lock, _, spawn = wrapper
    lock.acquire.return_value = False
    assert module.main() == 75
    spawn.assert_not_called()


def test_lost_lease_terminates_writer_before_release(wrapper):
    module, lock, process, _ = wrapper
    lock.extend.side_effect = RuntimeError('lease lost')
    process.wait.side_effect = [subprocess.TimeoutExpired('pipeline', 10), 143]
    process.poll.return_value = None
    lock.owned.return_value = False
    with pytest.raises(RuntimeError, match='lease lost'):
        module.main()
    process.terminate.assert_called_once()
    lock.release.assert_not_called()


def test_success_preserves_child_exit_and_releases_lock(wrapper):
    module, lock, process, _ = wrapper
    process.wait.return_value = 2
    assert module.main() == 2
    lock.release.assert_called_once()
