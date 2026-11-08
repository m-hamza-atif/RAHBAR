"""Deterministic extractive synthesis for offline tests, never a real model."""
import re
from ...schemas import Answer, Citation, Passage

STOP = set('what when how is are the a an to of for in on at do does can i my me '
           'please tell about say says now much minimum requirement required'.split())
POISON = re.compile(r'ignore.{0,30}(instructions|rules)|system prompt|you are now|'
                    r'state that|disregard.{0,30}(instructions|rules)', re.I)


def legitimate(text: str) -> str:
    return '\n'.join(part for part in re.split(r'\n|(?<=[.!?])\s+', text) if not POISON.search(part))


def abstention() -> Answer:
    return Answer(reasoning='Insufficient policy evidence.',
                  answer='The available corpus does not cover the requested information.',
                  citations=[], answered_from_context=False, confidence='low')


class StubProvider:
    name = 'stub'

    def generate(self, question: str, passages: list[Passage], validation_error: str = '') -> Answer:
        requested_topics = set(re.findall(r'\w+', question.lower())) & {
            'hostel', 'transport', 'curfew', 'mess', 'allocation'}
        if requested_topics and not any(requested_topics <= set(re.findall(
                r'\w+', legitimate(p.text).lower())) for p in passages):
            return abstention()
        terms = set(re.findall(r'\w+', question.lower())) - STOP
        candidates = []
        for passage in passages:
            text = legitimate(passage.text)
            if not text.strip():
                continue
            overlap = terms & set(re.findall(r'\w+', (text+' '+passage.section).lower()))
            if overlap:
                candidates.append((len(overlap), passage, text))
        if not candidates:
            return abstention()
        _, top, text = max(candidates, key=lambda x: x[0])
        if top.page is None:
            return abstention()
        return Answer(reasoning='Extracted from retrieved policy evidence.',
            answer=text[:3000], citations=[Citation(source=top.source, section=top.section, page=top.page)],
            answered_from_context=True, confidence='low')
