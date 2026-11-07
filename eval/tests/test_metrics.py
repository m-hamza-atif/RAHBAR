"""Offline evaluation metric and CI gate tests."""
import importlib.util
from pathlib import Path
import math

spec = importlib.util.spec_from_file_location('rahbar_eval', Path(__file__).parents[1]/'run_eval.py')
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


def test_recall_deduplicates_and_canonicalizes_clauses():
    expected = [{'source':'r.pdf','section':'Clause 1.21'}]*2
    actual = [{'source':'r.pdf','section':'1.21 Students are required'}]
    assert evaluation.recall_at_k(expected,actual,3)==1
    assert evaluation.recall_at_k(expected,actual,0)==0
    assert evaluation.recall_at_k([],actual,5) is None
    assert evaluation.section_key('9. Privacy & Data Security') != evaluation.section_key('9. Retakes')


def test_citations_require_exact_page_and_section():
    response={'retrieved':[{'source':'r.pdf','section':'Clause 1.21','page':4}],
              'citations':[{'source':'r.pdf','section':'Clause 1.21','page':4},
                           {'source':'r.pdf','section':'Clause 1.21','page':5}]}
    assert evaluation.citation_validity(response)==.5
    assert evaluation.citation_validity({'citations':[]}) is None


def test_summary_types_and_abstention():
    ref={'source':'r.pdf','section':'Clause 1.21','page':4}
    rows=[{'id':'a','type':'exact','relevant':[ref],'expect':'100',
           'response':{'retrieved':[ref],'citations':[ref]*3,'answer':'100%', 'answered_from_context':True}},
          {'id':'b','type':'abstain','must_abstain':True,'relevant':[],
           'response':{'retrieved':[],'citations':[],'answered_from_context':False}}]
    result=evaluation.summarise(rows)
    assert result['recall_at_5']==1 and result['citation_validity']==1
    assert result['abstention_correctness']==1
    assert result['by_type']['must_abstain']['recall_at_5'] is None
    assert result['by_type']['exact_term']['recall_at_3']==1


def test_gate_boundaries_missing_metrics_and_nan():
    good={'recall_at_5':.8,'citation_validity':.95,'abstention_correctness':1}
    assert evaluation.gate(good,{'recall_at_5':.85})==[]
    assert evaluation.gate(good,{'recall_at_5':.851})
    assert evaluation.gate({**good,'citation_validity':.949},None)
    assert evaluation.gate({**good,'abstention_correctness':.99},None)
    assert evaluation.gate({**good,'recall_at_5':math.nan},None)
    assert evaluation.gate({},None)


def test_real_golden_covers_all_categories():
    questions=evaluation.load_golden(Path(__file__).parents[1]/'golden.yaml')
    assert len(questions)>=18
    assert len({q['id'] for q in questions})==len(questions)
    assert {q['type'] for q in questions}=={'ordinary','version_sensitive','exact_term','must_abstain','prompt_injection'}
    assert sum(q.get('must_abstain',False) for q in questions)>=2


def test_cli_requires_baseline_and_never_overwrites_it_on_failure(tmp_path,monkeypatch):
    import httpx
    import json
    golden=tmp_path/'golden.yaml'
    golden.write_text('questions:\n- id: q1\n  type: ordinary\n  question: What policy?\n  relevant: [{source: r.pdf, section: Rule}]\n- id: q2\n  type: must_abstain\n  question: Hostel hours?\n  relevant: []\n  must_abstain: true\n')
    baseline=tmp_path/'baseline.json'
    output=tmp_path/'results.json'
    broken=[False]
    original=httpx.Client
    def handle(request):
        if request.method=='GET':
            return httpx.Response(200,json={'configuration':{}})
        assert request.headers['X-Cache-Bypass']=='true'
        question=json.loads(request.content)['question']
        ref={'source':'r.pdf','section':'Rule','page':1}
        grounded=question=='What policy?' or broken[0]
        return httpx.Response(200,json={'retrieved':[ref] if grounded else [],
            'citations':[ref] if grounded else [],'answered_from_context':grounded,'answer':'Policy'})
    monkeypatch.setattr(evaluation.httpx,'Client',lambda **kw:original(**kw,transport=httpx.MockTransport(handle)))
    arguments=['run_eval','--api','http://test','--golden',str(golden),'--baseline',str(baseline),'--out',str(output)]
    monkeypatch.setattr(evaluation.sys,'argv',arguments)
    assert evaluation.main()==1 and not baseline.exists()
    monkeypatch.setattr(evaluation.sys,'argv',arguments+['--update-baseline'])
    assert evaluation.main()==0
    old=baseline.read_bytes()
    broken[0]=True
    assert evaluation.main()==1 and baseline.read_bytes()==old


def test_golden_hash_is_portable_but_detects_changed_content(tmp_path):
    file=tmp_path/'golden.yaml'
    file.write_bytes(b'questions:\r\n- id: q1\r\n')
    windows=evaluation.golden_digest(file)
    file.write_bytes(b'questions:\n- id: q1\n')
    assert evaluation.golden_digest(file)==windows
    file.write_bytes(b'questions:\n- id: q2\n')
    assert evaluation.golden_digest(file)!=windows
