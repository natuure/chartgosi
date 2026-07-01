from typing import Literal

from pydantic import BaseModel, Field

AnswerDirection = Literal["up", "sideways", "down"]
RankingPeriodType = Literal["daily", "weekly", "monthly", "all_time"]


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


class QuestionListItem(BaseModel):
    id: str
    pattern: PatternResponse
    difficulty: str
    difficulty_label: str
    market_regime: str
    base_date: str
    public_accuracy: float | None = None
    total_answers: int = 0


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
    pattern: PatternResponse
    selected_answer: AnswerDirection
    correct_answer: AnswerDirection
    is_correct: bool
    actual_next_candles: list[dict]
    ai_explanation: str | None
    choice_distribution: dict[str, float]


class WrongNoteItem(BaseModel):
    answer_id: str
    question_id: str
    pattern: PatternResponse
    difficulty: str
    difficulty_label: str
    base_date: str
    selected_answer: AnswerDirection
    correct_answer: AnswerDirection
    created_at: str
    viewed_ai_explanation: bool
    ai_explanation: str | None


class WrongNotesResponse(BaseModel):
    items: list[WrongNoteItem]
    total: int
    limit: int
    offset: int


class WrongNoteDetailResponse(WrongNoteItem):
    actual_next_candles: list[dict]


class PatternStats(BaseModel):
    pattern: PatternResponse
    solved_count: int
    correct_count: int
    accuracy: float


class StatsResponse(BaseModel):
    solved_count: int
    correct_count: int
    wrong_count: int
    accuracy: float
    average_duration_ms: int | None
    pattern_stats: list[PatternStats]


class RankingItem(BaseModel):
    rank: int
    user_id: str
    nickname: str
    score: int
    accuracy: float
    solved_count: int
    correct_count: int


class RankingsResponse(BaseModel):
    period_type: RankingPeriodType
    items: list[RankingItem]


class MyRankingResponse(BaseModel):
    period_type: RankingPeriodType
    rank: int | None
    user_id: str
    nickname: str
    score: int
    accuracy: float
    solved_count: int
    correct_count: int
