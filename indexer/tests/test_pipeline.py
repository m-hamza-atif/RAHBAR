"""Indexer contracts and failure paths; offline, no model server."""
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock
import importlib
import json
import math

import httpx
import pytest

from pipeline.chunk import amplification, chunk, token_count
from pipeline.clean import clean
from pipeline.config import get_settings
from pipeline.embed import embed, stub_vector
from pipeline.extract import extract, strip_margins
from pipeline.models import Chunk, Document, Page
from pipeline.run import main

extract_module = importlib.import_module('pipeline.extract')
store_module = importlib.import_module('pipeline.store')


@pytest.fixture
def settings():
    return replace(get_settings(), embed_model='stub', llm_provider='stub')


def document(text, page=1):
    return Document('rules.md', '2026', False, [Page('rules.md', page, text)])


def test_clean_keeps_clauses_tables_and_headings():
    original = document('# Rules\nClause 1.21\n4.2  Registra-\ntion\x00\n\n\n| Fee | 2.00 |')
    result = clean(original)
    assert 'Registration' in result.pages[0].text
    assert 'Clause 1.21\n4.2' in result.pages[0].text
    assert '| Fee | 2.00 |' in result.pages[0].text
    assert '\x00' in original.pages[0].text


def test_margin_stripping_keeps_headings_clauses_and_body():
    pages = [Page('r.pdf', n, f'UNIVERSITY\n# Rules\n1.21 Attendance\nBody {n}\nFooter\n{n}')
             for n in range(1, 5)]
    result = strip_margins(pages)
    for page in result:
        assert 'UNIVERSITY' not in page.text and 'Footer' not in page.text
        assert '# Rules' in page.text and '1.21 Attendance' in page.text
        assert 'Body' in page.text


def mock_pdf(monkeypatch, text=''):
    page = MagicMock()
    page.extract_text.return_value = text
    page.find_tables.return_value = []
    context = MagicMock()
    context.__enter__.return_value.pages = [page]
    monkeypatch.setattr(extract_module.pdfplumber, 'open', lambda _: context)
    return page


def test_ocr_trigger_and_flag(monkeypatch):
    mock_pdf(monkeypatch)
    ocr = MagicMock(return_value='Recovered policy Clause 1.21')
    monkeypatch.setattr(extract_module, 'ocr_page', ocr)
    doc = extract('scan.pdf', '2023', True)
    ocr.assert_called_once_with('scan.pdf', 1)
    assert doc.pages[0].ocr and doc.superseded
    assert doc.pages[0].text == 'Recovered policy Clause 1.21'


def test_missing_ocr_logs_loss_without_crashing(monkeypatch, capsys):
    mock_pdf(monkeypatch)
    monkeypatch.setattr(extract_module, 'ocr_page', MagicMock(side_effect=RuntimeError('missing')))
    doc = extract('scan.pdf', '2023', True)
    assert not doc.pages[0].ocr
    assert json.loads(capsys.readouterr().out)['msg'] == 'ocr_unavailable'


def test_ocr_disabled_experiment(monkeypatch, capsys):
    mock_pdf(monkeypatch)
    ocr = MagicMock()
    monkeypatch.setattr(extract_module, 'ocr_page', ocr)
    assert not extract('scan.pdf', '2023', True, enable_ocr=False).pages[0].text
    ocr.assert_not_called()
    assert 'ocr_disabled' in capsys.readouterr().out


def test_text_pdf_skips_ocr(monkeypatch):
    mock_pdf(monkeypatch, 'Legitimate policy text with an existing text layer.')
    ocr = MagicMock()
    monkeypatch.setattr(extract_module, 'ocr_page', ocr)
    assert not extract('text.pdf', '2026', False).pages[0].ocr
    ocr.assert_not_called()


def test_pdf_tables_exclude_duplicate_prose(monkeypatch):
    page = mock_pdf(monkeypatch, 'Programme Fee BS 12000 and unrelated text')
    table = MagicMock()
    table.bbox = (0, 0, 100, 100)
    table.extract.return_value = [['Programme', 'Fee'], ['BS', '12000']]
    page.find_tables.return_value = [table]
    page.filter.return_value.extract_text.return_value = 'Unrelated prose'
    text = extract('table.pdf', '2026', False).pages[0].text
    assert '| BS | 12000 |' in text and text.count('12000') == 1
    predicate = page.filter.call_args.args[0]
    assert not predicate({'x0': 20, 'top': 20})
    assert predicate({'x0': 120, 'top': 20})


def test_html_and_markdown_extraction(tmp_path):
    file = tmp_path / 'fees.html'
    file.write_text('<html><nav>Menu</nav><h2>Fees</h2><table><tr><th>Programme</th>'
                    '<th>Fee</th></tr><tr><td>BS</td><td>12,000</td></tr></table></html>')
    text = clean(extract(str(file), '2026', False)).pages[0].text
    assert 'Menu' not in text and '## Fees' in text
    assert '| BS | 12,000 |' in text
    md = tmp_path / 'rules.md'
    md.write_text('---\ndoc_version: 2026\n---\n# Rules\nClause 1.21 attendance.')
    assert 'doc_version:' not in extract(str(md), '2026', False).pages[0].text


def test_structured_chunks_respect_sections_and_metadata():
    doc = document('## 1. Attendance\n\n' + 'Policy sentence. ' * 25 +
                   '\n\n## 2. Fees\n\nTuition is 12000 rupees.', page=4)
    pieces = chunk(doc, 20, 4)
    assert {c.section for c in pieces} == {'1. Attendance', '2. Fees'}
    assert all(token_count(c.text) <= 20 for c in pieces)
    assert all(c.page == 4 and c.doc_version == '2026' for c in pieces)
    assert all(set(c.metadata()) == {'source', 'section', 'page', 'doc_version', 'superseded'}
               for c in pieces)
    assert [c.id for c in pieces] == [c.id for c in chunk(doc, 20, 4)]
    assert len({c.id for c in pieces}) == len(pieces)
    assert all('Tuition' not in c.text for c in pieces if c.section == '1. Attendance')


def test_fixed_overlap_and_amplification_exact():
    doc = document(' '.join(f'token{i}' for i in range(25)))
    pieces = chunk(doc, 10, 2, 'fixed')
    assert [token_count(c.text) for c in pieces] == [10, 10, 9]
    assert pieces[0].text.split()[-2:] == pieces[1].text.split()[:2]
    assert math.isclose(amplification(doc, pieces), 29/25)
    assert amplification(document(''), []) == 0


def test_structured_prefers_paragraph_then_sentence():
    text = 'one two three four five six.\n\nseven eight nine ten eleven twelve.'
    structured = chunk(document(text), 9, 0)
    fixed = chunk(document(text), 9, 0, 'fixed')
    assert structured[0].text.endswith('six.')
    assert fixed[0].text.endswith('nine')
    sentences = chunk(document(text.replace('\n\n', ' ')), 9, 0)
    assert sentences[0].text.endswith('six.')


def test_pdf_clause_section_continues_to_next_page():
    doc = Document('r.pdf', '2026', False, [Page('r.pdf', 1, '4.4\nA student must register'),
                                           Page('r.pdf', 2, 'for the required courses.')])
    pieces = chunk(doc, 10, 2)
    assert all(c.section == 'Clause 4.4' for c in pieces)
    assert [c.page for c in pieces] == [1, 2]


@pytest.mark.parametrize('size,overlap', [(0, 0), (10, 10), (10, -1)])
def test_invalid_chunk_parameters(size, overlap):
    with pytest.raises(ValueError):
        chunk(document('policy'), size, overlap)


def test_config_aliases_and_validation(monkeypatch):
    monkeypatch.setenv('CHROMA_HOST', 'localhost:8001')
    monkeypatch.setenv('OLLAMA_BASE_URL', 'http://localhost:11434/')
    config = get_settings()
    assert (config.chroma_host, config.chroma_port) == ('localhost', 8001)
    assert config.ollama_url == 'http://localhost:11434'
    monkeypatch.setenv('CHUNK_SIZE', '10')
    with pytest.raises(ValueError):
        get_settings()


def test_stub_embeddings_are_deterministic_and_unit_length(settings):
    vectors, dim = embed(['CGPA 2.00', 'CGPA 2.00', 'tuition fees'], settings)
    assert dim == 384 and vectors[0] == vectors[1] != vectors[2]
    assert math.isclose(sum(v*v for v in vectors[0]), 1)
    assert sum(a*b for a, b in zip(stub_vector('minimum CGPA'), stub_vector('CGPA minimum'))) > .99


def test_ollama_batching_and_dimension_validation(settings, monkeypatch):
    module = importlib.import_module('pipeline.embed')
    client_class = httpx.Client
    calls = []
    def handler(request):
        payload = json.loads(request.content)
        calls.append(payload)
        return httpx.Response(200, json={'embeddings': [[1., 0., 0.]] * len(payload['input'])})
    monkeypatch.setattr(module.httpx, 'Client', lambda **kw: client_class(
        **kw, transport=httpx.MockTransport(handler)))
    vectors, dim = embed(['a', 'b', 'c'], replace(settings, embed_model='nomic-embed-text',
                        llm_provider='ollama-host', embed_batch_size=2))
    assert len(vectors) == 3 and dim == 3 and len(calls) == 2
    assert calls[0]['model'] == 'nomic-embed-text' and calls[0]['truncate'] is False


class FakeCollection:
    def __init__(self, metadata=None):
        self.metadata = metadata or {}
        self.rows = {}
    def modify(self, metadata):
        if 'hnsw:space' in metadata:
            raise ValueError('immutable distance configuration')
        self.metadata = metadata
    def count(self):
        return len(self.rows)
    def upsert(self, ids, documents, embeddings, metadatas):
        self.rows.update({i: (d, e, m) for i, d, e, m in zip(ids, documents, embeddings, metadatas)})
    def get(self, include):
        return {'ids': list(self.rows)}
    def delete(self, ids):
        for key in ids:
            del self.rows[key]


class FakeClient:
    def __init__(self):
        self.collection = FakeCollection()
    def get_or_create_collection(self, **kwargs):
        return self.collection
    def delete_collection(self, name):
        self.collection = FakeCollection()
    def create_collection(self, name, metadata):
        self.collection = FakeCollection(metadata)
        return self.collection


def test_store_idempotence_pin_stale_removal_and_cache(settings, monkeypatch):
    client = FakeClient()
    client.collection.metadata = {'hnsw:space': 'cosine'}
    invalidate = MagicMock(return_value=2)
    monkeypatch.setattr(store_module, 'get_client', lambda _: client)
    monkeypatch.setattr(store_module, 'invalidate_cache', invalidate)
    chunks = chunk(document('## Rules\nAttendance is required.'), 10, 2)
    vectors, dim = embed([c.text for c in chunks], settings)
    assert store_module.store(chunks, vectors, settings) == len(chunks)
    assert store_module.store(chunks, vectors, settings) == len(chunks)
    assert invalidate.call_count == 4
    assert client.collection.metadata['embed_model'] == 'stub'
    assert client.collection.metadata['embed_dim'] == dim
    assert client.collection.metadata['index_state'] == 'ready'
    changed = [replace(chunks[0], id='replacement')]
    store_module.store(changed, [vectors[0]], settings)
    assert set(client.collection.rows) == {'replacement'}


def test_cache_outage_prevents_modifying_old_index(settings, monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(store_module, 'get_client', lambda _: client)
    monkeypatch.setattr(store_module, 'invalidate_cache', MagicMock(side_effect=RuntimeError('Redis down')))
    with pytest.raises(RuntimeError):
        store_module.store([Chunk('1', 'policy', 'r.md', 'Rule', 1, '2026', False)], [[1.]], settings)
    assert client.collection.metadata == {} and client.collection.count() == 0


def test_postwrite_cache_failure_leaves_index_unready(settings, monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(store_module, 'get_client', lambda _: client)
    monkeypatch.setattr(store_module, 'invalidate_cache', MagicMock(side_effect=[0, RuntimeError('down')]))
    with pytest.raises(RuntimeError):
        store_module.store([Chunk('1', 'policy', 'r.md', 'Rule', 1, '2026', False)], [[1.]], settings)
    assert client.collection.metadata['index_state'] == 'building'


def test_invalid_vectors_fail_before_cache_or_store(settings, monkeypatch):
    invalidate = MagicMock()
    monkeypatch.setattr(store_module, 'invalidate_cache', invalidate)
    c = Chunk('1', 'policy', 'r.md', 'Rule', 1, '2026', False)
    for vectors in ([], [[float('nan')]], [[0.]], [[1.], [2.]]):
        with pytest.raises(ValueError):
            store_module.store([c], vectors, settings)
    invalidate.assert_not_called()


def test_redis_invalidation_only_deletes_our_namespace(settings, monkeypatch):
    import redis
    connection = MagicMock()
    client = connection.__enter__.return_value
    client.scan_iter.return_value = [b'rahbar:cache:a', b'rahbar:cache:b']
    client.delete.return_value = 1
    monkeypatch.setattr(redis.Redis, 'from_url', lambda *args, **kwargs: connection)
    assert store_module.invalidate_cache(settings) == 2
    client.scan_iter.assert_called_once_with(match='rahbar:cache:*', count=500)
    client.flushdb.assert_not_called()


def test_cli_errors_are_json_and_nonzero(settings, monkeypatch, capsys):
    module = importlib.import_module('pipeline.run')
    monkeypatch.setattr('sys.argv', ['pipeline.run'])
    monkeypatch.setattr(module, 'get_settings', lambda: settings)
    monkeypatch.setattr(module, 'run_pipeline', MagicMock(side_effect=ValueError('bad corpus')))
    assert main() == 1
    records = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert records[-1]['msg'] == 'indexer_failed'


def test_fixture_pipeline_wires_every_stage(settings, monkeypatch):
    from pipeline.run import run_pipeline
    fixtures = Path(__file__).resolve().parents[2] / 'eval' / 'fixtures'
    captured = []
    def store(chunks, vectors, config):
        captured.extend(chunks)
        assert len(vectors) == len(chunks)
        return len(chunks)
    monkeypatch.setattr(store_module, 'store', store)
    assert run_pipeline(replace(settings, corpus_dir=str(fixtures))) > 0
    assert any(c.superseded for c in captured)
    assert any('| BS (all disciplines) | 10,000 |' in c.text for c in captured)

def test_model_dimension_change_recreates_collection(settings, monkeypatch):
    client = FakeClient()
    client.collection = FakeCollection({'embed_model': 'old', 'embed_dim': 768})
    client.collection.rows['old-id'] = ('old', [1.] * 768, {})
    monkeypatch.setattr(store_module, 'get_client', lambda _: client)
    monkeypatch.setattr(store_module, 'invalidate_cache', lambda _: 0)
    c = Chunk('new', 'policy', 'r.md', 'Rule', 1, '2026', False)
    assert store_module.store([c], [[1., 0.]], settings) == 1
    assert client.collection.metadata['embed_dim'] == 2
    assert set(client.collection.rows) == {'new'}


def test_malformed_ollama_response_is_rejected(settings, monkeypatch):
    module = importlib.import_module('pipeline.embed')
    client_class = httpx.Client
    monkeypatch.setattr(module.httpx, 'Client', lambda **kw: client_class(
        **kw, transport=httpx.MockTransport(lambda _: httpx.Response(
            200, json={'embeddings': [[1.], [1., 2.]]}))))
    with pytest.raises(ValueError, match='consistent dimensions'):
        embed(['a', 'b'], replace(settings, embed_model='nomic-embed-text', llm_provider='ollama-host'))
