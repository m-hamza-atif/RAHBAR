#!/usr/bin/env python3
"""Score a running RAHBAR against a golden set, and gate CI on the result (section 5).

    python eval/run_eval.py --api http://<ingress>                 # your corpus
    python eval/run_eval.py --api ... --golden eval/fixtures/golden.fixture.yaml
    python eval/run_eval.py --api ... --update-baseline            # after a deliberate improvement

Exit code 0 when every gate passes, 1 when any fails. CI relies on that exit code.

The gate uses measured retrieval references and verified citation triples.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import re
import math
import hashlib
from pathlib import Path

import httpx
import yaml

HERE = Path(__file__).resolve().parent

# The gate from section 5.4. Change these only with a reason written in docs/PIPELINE.md.
MAX_RECALL5_DROP = 0.05        # recall@5 may fall at most 5 points below the baseline
MIN_CITATION_VALIDITY = 0.95   # at least 95% of citations must match retrieved passages
REQUIRED_ABSTENTION = 1.0      # every must-abstain question must be declined


def golden_digest(path: Path) -> str:
    """Hash UTF-8 text with canonical LF endings, independent of Git checkout OS."""
    return hashlib.sha256(path.read_text(encoding='utf-8-sig').encode('utf-8')).hexdigest()


def load_golden(path: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    questions = data.get("questions") or []
    if not questions:
        sys.exit(f"no questions in {path}")
    if len({q['id'] for q in questions}) != len(questions):
        raise ValueError('golden question ids must be unique')
    return questions


def ask(client: httpx.Client, api: str, question: str, bypass_cache: bool = True) -> dict:
    """POST one question and return the AskResponse as a dict (see api/app/schemas.py)."""
    response = client.post(f"{api.rstrip('/')}/api/ask", json={"question": question},
                           headers={'X-Cache-Bypass': str(bypass_cache).lower()})
    response.raise_for_status()
    return response.json()


def recall_at_k(relevant: list[dict], retrieved: list[dict], k: int) -> float | None:
    """Fraction of the relevant (source, section) pairs found in the top k retrieved.
    Return None when the question has no relevant passages (must-abstain questions)."""
    expected = {(p['source'], section_key(p['section'])) for p in relevant}
    if not expected:
        return None
    found = {(p['source'], section_key(p['section'])) for p in retrieved[:k]}
    return len(expected & found) / len(expected)


def section_key(value: str) -> str:
    text = value.strip().lstrip('#').strip().lower()
    clause = re.match(r'^(?:clause\s+)?(\d+\.\d+(?:\.\d+)*)(?:\b|$)', text)
    return clause.group(1) if clause else re.sub(r'\s+', ' ', text)


def citation_validity(response: dict) -> float | None:
    """Fraction of the response's citations that match a passage in response['retrieved'].
    Return None when there are no citations."""
    citations = response.get('citations') or []
    if not citations:
        return None
    refs = {(p['source'], p['section'], p.get('page')) for p in response.get('retrieved', [])}
    return sum((c['source'], c['section'], c.get('page')) in refs for c in citations)/len(citations)


def summarise(rows: list[dict]) -> dict:
    """Overall recall@3, recall@5, citation validity and abstention correctness, plus
    recall@5 broken down by question type. This dict becomes results.json."""
    def mean(values: list) -> float | None:
        measured = [x for x in values if x is not None]
        return sum(measured)/len(measured) if measured else None
    per_type: dict[str, list[tuple[float | None, float | None]]] = {}
    evaluated = []
    valid, total = 0, 0
    abstentions = []
    for row in rows:
        response = row['response']
        r3 = recall_at_k(row.get('relevant', []), response.get('retrieved', []), 3)
        r5 = recall_at_k(row.get('relevant', []), response.get('retrieved', []), 5)
        rate = citation_validity(response)
        n = len(response.get('citations') or [])
        total += n
        valid += round((rate or 0)*n)
        if row.get('must_abstain'):
            abstentions.append(not response.get('answered_from_context', True)
                               and not response.get('citations'))
        typ = {'version': 'version_sensitive', 'exact': 'exact_term',
               'abstain': 'must_abstain', 'injection': 'prompt_injection'}.get(row['type'], row['type'])
        per_type.setdefault(typ, []).append((r3, r5))
        evaluated.append({**row, 'recall_at_3': r3, 'recall_at_5': r5,
                          'citation_validity': rate,
                          'expected_text_match': str(row['expect']).lower() in response.get('answer', '').lower()
                          if row.get('expect') else None})
    return {'recall_at_3': mean([r['recall_at_3'] for r in evaluated]),
            'recall_at_5': mean([r['recall_at_5'] for r in evaluated]),
            'citation_validity': valid/total if total else 1.0,
            'citation_count': total, 'valid_citation_count': valid,
            'abstention_correctness': mean(abstentions),
            'must_abstain_count': len(abstentions),
            'grounded_answer_rate': mean([r['response'].get('answered_from_context', False)
                                         for r in rows if not r.get('must_abstain')]),
            'by_type': {typ: {'count': len(values), 'recall_at_3': mean([v[0] for v in values]),
                             'recall_at_5': mean([v[1] for v in values])}
                        for typ, values in per_type.items()}, 'rows': evaluated}


def gate(results: dict, baseline: dict | None) -> list[str]:
    """Return one message per failed gate (section 5.4); an empty list means pass."""
    failures = []
    for name in ['recall_at_5', 'citation_validity', 'abstention_correctness']:
        value = results.get(name)
        if not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
            failures.append(f'{name} is missing or invalid')
    if failures:
        return failures
    if results['citation_validity'] < MIN_CITATION_VALIDITY:
        failures.append('citation validity is below 0.95')
    if results['abstention_correctness'] < REQUIRED_ABSTENTION:
        failures.append('must-abstain correctness is below 1.0')
    if baseline is not None:
        old = baseline.get('recall_at_5')
        if not isinstance(old, (int, float)) or not math.isfinite(old) or not 0 <= old <= 1:
            failures.append('baseline recall_at_5 is missing or invalid')
        elif results['recall_at_5'] + 1e-9 < old - MAX_RECALL5_DROP:
            failures.append('recall@5 fell more than five percentage points')
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate RAHBAR against a golden set.")
    parser.add_argument("--api", required=True, help="base URL, e.g. http://192.168.49.2")
    parser.add_argument("--host", help="Host header, when your Ingress rule names a host")
    parser.add_argument('--use-cache', action='store_true', help='include cache in evaluation; default bypasses it')
    parser.add_argument('--timeout', type=float, default=300.0, help='per-request timeout including model loading/retry')
    parser.add_argument("--golden", type=Path, default=HERE / "golden.yaml")
    parser.add_argument("--baseline", type=Path, default=HERE / "baseline.json")
    parser.add_argument("--out", type=Path, default=HERE / "results.json")
    parser.add_argument("--update-baseline", action="store_true",
                        help="write these results as the new baseline")
    args = parser.parse_args()

    questions = load_golden(args.golden)
    rows = []
    headers = {"Host": args.host} if args.host else {}
    with httpx.Client(timeout=args.timeout, headers=headers) as client:
        ready = client.get(f'{args.api.rstrip("/")}/readyz')
        ready.raise_for_status()
        configuration = ready.json().get('configuration', {})
        for q in questions:
            started = time.perf_counter()
            response = ask(client, args.api, q["question"], bypass_cache=not args.use_cache)
            rows.append({
                "id": q["id"], "type": q.get("type", "ordinary"),
                "must_abstain": bool(q.get("must_abstain", False)),
                "relevant": q.get("relevant") or [],
                "expect": q.get("expect"),
                "response": response,
                "seconds": round(time.perf_counter() - started, 2),
            })
            print(f"  {q['id']:<5} {rows[-1]['seconds']:>6.2f}s  {q['question'][:60]}")

    results = summarise(rows)
    baseline = json.loads(args.baseline.read_text()) if args.baseline.exists() else None
    failures = gate(results, baseline)
    if baseline is None and not args.update_baseline:
        failures.append('baseline missing; create it explicitly with --update-baseline')
    golden_hash = golden_digest(args.golden)
    if baseline and baseline.get('golden_sha256') not in (None, golden_hash):
        failures.append('baseline belongs to a different golden dataset')

    results["golden"] = str(args.golden)
    results["questions"] = len(rows)
    results['configuration'] = configuration
    results['golden_sha256'] = golden_hash
    args.out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nresults written to {args.out}")
    if args.update_baseline and not failures:
        args.baseline.write_text(json.dumps({k: v for k, v in results.items() if k != 'rows'},
                                          indent=2), encoding="utf-8")
        print(f"baseline updated: {args.baseline}")

    if failures:
        print("\nGATE FAILED")
        for message in failures:
            print(f"  - {message}")
        return 1
    print("\ngate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
