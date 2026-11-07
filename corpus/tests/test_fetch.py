"""Offline integrity checks for the download/manifest boundary."""
import importlib.util
import json
from pathlib import Path

import httpx
import pytest

spec = importlib.util.spec_from_file_location("corpus_fetch", Path(__file__).parents[1] / "fetch.py")
assert spec and spec.loader
fetcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetcher)


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(fetcher, "RAW", tmp_path / "raw")
    monkeypatch.setattr(fetcher, "MANIFEST", tmp_path / "MANIFEST.md")
    monkeypatch.setattr(fetcher, "SOURCES", tmp_path / "sources.yaml")
    monkeypatch.setattr(fetcher, "PAUSE_SECONDS", 0)
    fetcher.SOURCES.write_text('documents:\n- name: Fees\n  url: https://example.test/fees\n'
                               '  doc_version: "2026"\n  superseded: false\n'
                               '  properties: [4, 7]\n')
    return tmp_path


def test_url_encoding_and_drive():
    assert fetcher.normalise("https://example.test/a b%20c.pdf") == (
        "https://example.test/a%20b%20c.pdf")
    assert fetcher.normalise("https://drive.google.com/file/d/abc/view?usp=sharing") == (
        "https://drive.google.com/uc?export=download&id=abc")


def test_rejects_invalid_documents():
    with pytest.raises(ValueError, match="not a PDF"):
        fetcher.inspect_content(b"<html>error</html>", ".pdf")
    with pytest.raises(Exception):
        fetcher.inspect_content(b"%PDF-invalid", ".pdf")
    with pytest.raises(ValueError, match="not an HTML"):
        fetcher.inspect_content(b"unstructured error", ".html")


def test_download_reuse_and_tamper_detection(workspace, monkeypatch):
    calls = []
    client_class = httpx.Client

    def handler(request):
        calls.append(request.url)
        return httpx.Response(200, headers={"content-type": "text/html"},
                              content=b"<!doctype html><html><table><tr><td>12000</td></tr></table></html>")

    monkeypatch.setattr(fetcher.httpx, "Client", lambda **kw: client_class(
        **kw, transport=httpx.MockTransport(handler)))
    assert fetcher.fetch(False) == 0
    entry = json.loads((fetcher.RAW / "_index.json").read_text())[0]
    assert entry["pages"] == 0
    assert entry["properties"] == [4, 7]
    assert entry["superseded"] is False
    assert fetcher.verify() == 0
    assert fetcher.fetch(False) == 0
    assert len(calls) == 1
    (fetcher.RAW / entry["file"]).write_text("tampered")
    assert fetcher.verify() == 1
    assert fetcher.fetch(False) == 0
    assert len(calls) == 2


def test_empty_manifest_cannot_pass(workspace):
    fetcher.MANIFEST.write_text("# empty")
    assert fetcher.verify() == 1


def test_boolean_metadata_is_not_coerced(workspace):
    fetcher.SOURCES.write_text('documents:\n- name: Rules\n  url: https://example.test\n'
                               '  superseded: "false"\n')
    with pytest.raises(SystemExit, match="YAML boolean"):
        fetcher.load_sources()
