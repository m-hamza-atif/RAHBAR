"""The contracts. Change them only with your partner's review: the UI, the
evaluation script and your tests all depend on these shapes.

`Answer` is what the model must produce (section 3.4). `AskResponse` is what
the API returns to the UI and to eval/run_eval.py. The model's `reasoning` is
never sent to the user.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ConfigDict, field_validator


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)

    @field_validator("question")
    @classmethod
    def meaningful_question(cls, value: str) -> str:
        if len(value.strip()) < 3:
            raise ValueError("question must have at least three non-padding characters")
        return value.strip()


class Passage(BaseModel):
    """One retrieved chunk, as the retriever hands it to the generator."""

    chunk_id: str
    text: str
    source: str
    section: str
    page: int | None = None
    score: float = Field(description="Similarity, higher is closer (1 - cosine distance).")


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    source: str
    section: str
    page: int = Field(ge=1)


class Answer(BaseModel):
    """The model's output contract. Send its JSON schema to the model, then validate."""

    model_config = ConfigDict(extra="forbid", strict=True)

    reasoning: str = Field(max_length=300, description='One brief evidence-summary sentence, not private reasoning.')
    answer: str
    citations: list[Citation]
    answered_from_context: bool = Field(description=(
        'True when this answer is supported by the supplied evidence and citations. '
        'False only for refusal with no citations and low confidence.'))
    confidence: Literal["high", "medium", "low"]


class RetrievedRef(BaseModel):
    """What the response says was retrieved. eval/run_eval.py scores against this."""

    chunk_id: str
    source: str
    section: str
    page: int | None = None
    score: float


class AskResponse(BaseModel):
    request_id: str
    answer: str
    citations: list[Citation]
    answered_from_context: bool
    confidence: Literal["high", "medium", "low"]
    retrieved: list[RetrievedRef]
    provider: str
    cached: bool = False
