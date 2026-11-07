"""Measured full-corpus chunk/cache experiments. Never runs from API startup.

Prepare OCR on WSL with --extract-only. On Windows, --documents points to that
ignored extraction cache and Ollama stays bound to localhost. Model vectors are
cached by exact text and Ollama digest to avoid redundant inference and storage.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import sys

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'indexer'), str(ROOT/'api'), str(ROOT/'eval')]
from pipeline.chunk import chunk, token_count  # noqa: E402
from pipeline.clean import clean  # noqa: E402
from pipeline.config import get_settings as index_settings  # noqa: E402
from pipeline.embed import embed  # noqa: E402
from pipeline.extract import extract  # noqa: E402
from pipeline.logging import configure_logging, log  # noqa: E402
from pipeline.models import Document, Page  # noqa: E402
from pipeline.run import discover  # noqa: E402
from pipeline.store import store, get_client  # noqa: E402
from app.config import get_settings as api_settings  # noqa: E402
from app.embeddings import embed_query  # noqa: E402
from app.retrieval.chroma import ChromaRetriever  # noqa: E402
from app.services.cache import cosine, scope  # noqa: E402
from run_eval import load_golden, summarise, golden_digest  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extract-only', action='store_true')
    parser.add_argument('--api', help='optional running API for the restored pin-mismatch experiment')
    parser.add_argument('--documents', type=Path, default=ROOT/'corpus/raw/phase4-cleaned.json')
    args = parser.parse_args()
    configure_logging()
    if args.extract_only:
        documents = [asdict(clean(extract(str(p), v, old)))
                     for p, v, old in discover(str(ROOT/'corpus/raw'))]
        args.documents.write_text(json.dumps(documents), encoding='utf-8')
        return
    docs = [Document(d['source'], d['doc_version'], d['superseded'],
                     [Page(**p) for p in d['pages']])
            for d in json.loads(args.documents.read_text(encoding='utf-8'))]
    settings = replace(index_settings(), chroma_host='localhost', chroma_port=8001,
                       embed_model='nomic-embed-text', llm_provider='ollama-host',
                       ollama_url='http://localhost:11434')
    api = replace(api_settings(), chroma_host='localhost', chroma_port=8001,
                  embed_model=settings.embed_model, embed_dim=768, llm_provider='ollama-host',
                  ollama_url=settings.ollama_url)
    tags = httpx.get(settings.ollama_url+'/api/tags').json()['models']
    digest = next(m['digest'] for m in tags if m['name'].split(':')[0] == settings.embed_model)
    cache_path = ROOT/'corpus/raw/phase4-vectors.json'
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    if cache.get('model_digest') != digest:
        cache = {'model_digest': digest, 'vectors': {}}
    vectors = cache['vectors']

    def encode(texts: list[str]) -> list[list[float]]:
        missing = list(dict.fromkeys(t for t in texts if hashlib.sha256(t.encode()).hexdigest() not in vectors))
        if missing:
            generated, _ = embed(missing, settings)
            for text, vector in zip(missing, generated):
                vectors[hashlib.sha256(text.encode()).hexdigest()] = vector
            cache_path.write_text(json.dumps(cache), encoding='utf-8')
        return [vectors[hashlib.sha256(t.encode()).hexdigest()] for t in texts]

    questions = load_golden(ROOT/'eval/golden.yaml')
    queries = {q['id']: embed_query(q['question'], api) for q in questions}
    configs = []
    all_chunks = {}
    for size, overlap, strategy in [(256, 32, 'structure'), (512, 64, 'structure'),
                                     (1024, 128, 'structure'), (100, 0, 'fixed')]:
        pieces = [c for d in docs for c in chunk(d, size, overlap, strategy)]
        name = f'rahbar_tune_{size}_{overlap}_{strategy}'
        store(pieces, encode([c.text for c in pieces]), replace(settings, collection=name))
        retriever = ChromaRetriever(replace(api, collection=name))
        rows = []
        for q in questions:
            passages = [p for p in retriever.retrieve(q['question'], 5, queries[q['id']])
                        if p.score >= api.relevance_floor]
            rows.append({**q, 'response': {'retrieved': [p.model_dump(exclude={'text'}) for p in passages],
                                          'citations': [], 'answered_from_context': bool(passages)}})
        metrics = summarise(rows)
        original = sum(token_count(p.text) for d in docs for p in d.pages)
        config = {'size': size, 'overlap': overlap, 'strategy': strategy, 'chunks': len(pieces),
                  'storage_amplification': sum(token_count(c.text) for c in pieces)/original,
                  'recall_at_3': metrics['recall_at_3'], 'recall_at_5': metrics['recall_at_5'],
                  'by_type': metrics['by_type'], 'retrieval_only': True}
        configs.append(config)
        all_chunks[size] = pieces
        log('tuning_measured', **config)
    candidates = [c for c in configs if c['strategy'] == 'structure']
    selected = max(candidates, key=lambda c: (c['recall_at_5'], c['recall_at_3'], -abs(c['size']-512)))
    shipped = all_chunks[selected['size']]
    store(shipped, encode([c.text for c in shipped]), replace(settings, collection='rahbar_policies'))

    pairs = [
        ('What minimum CGPA is required for graduation?', 'What CGPA do I need to graduate?', True),
        ('What is the BS tuition fee per credit hour?', 'How much tuition does each BS credit hour cost?', True),
        ('What minimum attendance is required?', 'What is the required minimum attendance?', True),
        ('What minimum CGPA is required for graduation?', 'What minimum CGPA avoids academic warning?', False),
        ('What is the tuition fee?', 'What is the admission fee?', False),
        ('What is the minimum attendance?', 'What is the minimum graduation CGPA?', False),
        ('Can I miss lectures?', 'Can I miss the final examination?', False),
        ('What is the BS tuition fee?', 'What is the PhD tuition fee?', False),
    ]
    measured = []
    for a, b, same in pairs:
        similarity = cosine(embed_query(a, api), embed_query(b, api))
        measured.append({'a': a, 'b': b, 'same_intent': same, 'similarity': similarity,
                         'same_cache_scope': scope(a) == scope(b)})
    negatives = [p['similarity'] for p in measured if not p['same_intent'] and p['same_cache_scope']]
    high = min(1.0, max(.95, round(max(negatives)+.001, 3)))
    thresholds = []
    for threshold in [.80, .90, high]:
        hits = [p for p in measured if p['same_cache_scope'] and p['similarity'] >= threshold]
        thresholds.append({'threshold': threshold, 'false_hits': sum(not p['same_intent'] for p in hits),
                           'true_hits': sum(p['same_intent'] for p in hits)})
    cache_threshold = min(t['threshold'] for t in thresholds if t['false_hits'] == 0)

    scanned = next(d for d in docs if d.source.startswith('faculty-entrepreneurship'))
    disabled = clean(extract(str(ROOT/'corpus/raw'/scanned.source), scanned.doc_version,
                             scanned.superseded, enable_ocr=False))
    failures = {'A': {'source': scanned.source, 'ocr_enabled_chunks': len(chunk(scanned, 512, 64)),
                      'ocr_disabled_chunks': len(chunk(disabled, 512, 64)),
                      'ocr_disabled_chars': sum(len(p.text) for p in disabled.pages)},
                'B': {'fixed': configs[-1], 'structure': selected}}
    retriever = ChromaRetriever(replace(api, collection='rahbar_policies'))
    collection = retriever.collection()
    question = 'Can students register for more than five courses provided they are not getting ahead of their batch?'
    vector = embed_query(question, api)
    def lookup(where):
        r = collection.query(query_embeddings=[vector], n_results=5, where=where,
                             include=['documents', 'metadatas', 'distances'])
        return [{'id': key, **meta, 'score': 1-distance, 'excerpt': text[:200]}
                for key, meta, distance, text in zip(r['ids'][0], r['metadatas'][0],
                                                    r['distances'][0], r['documents'][0])]
    failures['E'] = {'question': question, 'filtered': lookup({'superseded': False}),
                      'filter_disabled': lookup(None)}
    report = {'configuration': {'embedding_model': settings.embed_model, 'embedding_dim': 768,
               'model_digest': digest, 'relevance_floor': api.relevance_floor,
               'golden_sha256': golden_digest(ROOT/'eval/golden.yaml'),
               'documents_sha256': hashlib.sha256(args.documents.read_bytes()).hexdigest()},
              'chunking': configs, 'selected_chunking': selected,
              'cache_pairs': measured, 'cache_thresholds': thresholds,
              'selected_cache_threshold': cache_threshold, 'failure_modes': failures}
    if args.api:
        original = dict(collection.metadata)
        try:
            collection.modify(metadata={**original, 'embed_model': 'deliberately-wrong-embedding'})
            with httpx.Client(base_url=args.api, headers={'X-Request-ID': 'failure-C-demo'}) as client:
                ready, health = client.get('/readyz'), client.get('/healthz')
                query = client.post('/api/ask', json={'question': 'What is the graduation CGPA?'})
                if (ready.status_code, health.status_code, query.status_code) != (503, 200, 503):
                    raise RuntimeError('embedding guardrail did not fail closed')
                failures['C'] = {'ready_status': ready.status_code, 'health_status': health.status_code,
                                 'query_status': query.status_code, 'response': ready.json()}
        finally:
            collection.modify(metadata=original)
    (ROOT/'eval/experiments.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    # Tuning collections are temporary: retain only the selected production collection.
    client = get_client(settings)
    for c in configs:
        client.delete_collection(f"rahbar_tune_{c['size']}_{c['overlap']}_{c['strategy']}")
    cache_path.unlink(missing_ok=True)
    log('experiments_complete', selected_size=selected['size'], cache_threshold=cache_threshold)


if __name__ == '__main__':
    main()
