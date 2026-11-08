"""Provider protocol; raw output is validated centrally, with one retry."""
from dataclasses import dataclass
from typing import Protocol
from ...schemas import Answer, Passage


@dataclass
class Generation:
    text: str
    prompt_tokens: int
    completion_tokens: int


def count_tokens(text: str) -> int:
    """Whitespace estimate when a provider does not report actual token usage."""
    return len(text.split())


class LLMProvider(Protocol):
    name: str

    def generate(self, question: str, passages: list[Passage],
                 validation_error: str = '') -> Answer | str | Generation: ...
