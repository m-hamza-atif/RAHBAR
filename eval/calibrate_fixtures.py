"""Reproduce the offline-model fixture floor calibration against local services."""
import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'api'),str(ROOT/'indexer'),str(ROOT/'eval')]
from pipeline.config import get_settings  # noqa: E402
from pipeline.run import run_pipeline  # noqa: E402
from pipeline.logging import configure_logging  # noqa: E402
from run_eval import load_golden,ask,summarise,gate,golden_digest  # noqa: E402


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--update-baseline',action='store_true')
    args=parser.parse_args()
    configure_logging()
    settings=replace(get_settings(),chroma_host='localhost',chroma_port=8001,
        collection='rahbar_ci_fixtures',embed_model='stub',llm_provider='stub',
        corpus_dir=str(ROOT/'eval/fixtures'))
    run_pipeline(settings)
    os.environ.update(RETRIEVER='chroma',LLM_PROVIDER='stub',EMBED_MODEL='stub',
        EMBED_DIM='384',CHROMA_HOST='localhost:8001',CHROMA_COLLECTION=settings.collection,REDIS_FAKE='false')
    from fastapi.testclient import TestClient
    from app.main import app
    path=ROOT/'eval/fixtures/golden.fixture.yaml'
    measurements=[]
    summaries=[]
    with TestClient(app) as client:
        for floor in [.15,.25,.35]:
            app.state.settings=replace(app.state.settings,relevance_floor=floor)
            rows=[{**q,'response':ask(client,'http://testserver',q['question'])} for q in load_golden(path)]
            result=summarise(rows)
            measurements.append({'relevance_floor':floor,**{k:result[k] for k in [
                'recall_at_5','citation_validity','abstention_correctness','grounded_answer_rate']}})
            summaries.append(result)
    chosen=max(range(len(measurements)),key=lambda i:(measurements[i]['recall_at_5'],
        measurements[i]['abstention_correctness'],measurements[i]['relevance_floor']))
    result=summaries[chosen]
    floor=measurements[chosen]['relevance_floor']
    result.update(golden='eval/fixtures/golden.fixture.yaml',
        golden_sha256=golden_digest(path),questions=len(rows),
        configuration={'profile':'CI stub fixtures','embed_model':'stub','embed_dim':384,
        'llm_provider':'stub','relevance_floor':floor,'cache_threshold':.9,'collection':settings.collection})
    target=ROOT/'eval/fixtures/baseline.fixture.json'
    baseline=json.loads(target.read_text()) if target.exists() else None
    failures=gate(result,baseline)
    (ROOT/'eval/fixtures/results.fixture.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    (ROOT/'eval/fixture-calibration.json').write_text(json.dumps({'measurements':measurements,
        'selected_relevance_floor':floor},indent=2),encoding='utf-8')
    if args.update_baseline and not failures:
        target.write_text(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2),encoding='utf-8')
    print(json.dumps({'selected_floor':floor,'gate_failures':failures}))
    return int(bool(failures))


if __name__=='__main__':
    raise SystemExit(main())
