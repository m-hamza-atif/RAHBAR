"""Preserve obligation levels in complex cited clauses without paraphrase."""
import re

from ..providers.llm.stub import POISON
from ..schemas import Answer, Citation, Passage


def preserve_obligations(answer: Answer, passages: list[Passage]) -> Answer:
    if not answer.answered_from_context:
        return answer
    cited = {(c.source, c.section) for c in answer.citations}
    complex_clauses = {
        (p.source, p.section) for p in passages
        if (p.source, p.section) in cited
        and len(set(re.findall(r'\b(must|should|may)\b', p.text.lower()))) > 1
        and len(re.findall(r'(?:^|\n)\s*[a-z]\)', p.text)) >= 2
        and not POISON.search(p.text)
    }
    if not complex_clauses:
        return answer
    evidence = sorted((p for p in passages if (p.source, p.section) in complex_clauses
                       and p.page is not None and not POISON.search(p.text)),
                      key=lambda p: (p.source, p.section, p.page or 0))
    if not evidence:
        return answer
    citations = [Citation(source=p.source, section=p.section, page=p.page)
                 for p in evidence if p.page is not None]
    return Answer(reasoning='Quoted the retrieved operative clauses to preserve distinct obligation levels.',
                  answer='The policy states:\n\n' + '\n\n'.join(p.text for p in evidence),
                  citations=citations, answered_from_context=True, confidence=answer.confidence)
