from typing import Literal

from pydantic import BaseModel, Field

AnswerDirection = Literal["up", "sideways", "down"]


class PatternResponse(BaseModel):
    id: str
    slug: str
    name: str
    question_count: int = 0


class QuestionResponse(BaseModel):
    id: str
    pattern: PatternResponse
    difficulty: str
    difficulty_label: str
    market_regime: str
    base_date: str
    chart_data: list[dict]
    hidden_candles_count: int = 5
    answer_options: list[AnswerDirection] = ["up", "sideways", "down"]
    public_accuracy: float | None = None


class AnswerSubmit(BaseModel):
    selected_answer: AnswerDirection
    confidence: int | None = Field(default=None, ge=0, le=100)
    reason_tags: list[str] = []
    answer_duration_ms: int | None = Field(default=None, ge=0)
    is_retry: bool = False


class AnswerSubmitResponse(BaseModel):
    answer_id: str
    question_id: str
    selected_answer: AnswerDirection
    correct_answer: AnswerDirection
    is_correct: bool


class AnswerResultResponse(BaseModel):
    answer_id: str
    question_id: str
    selected_answer: AnswerDirection
    correct_answer: AnswerDirection
    is_correct: bool
    actual_next_candles: list[dict]
    ai_explanation: str | None
    choice_distribution: dict[str, float]
