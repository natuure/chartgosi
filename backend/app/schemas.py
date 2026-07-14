from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

AnswerDirection = Literal["up", "sideways", "down"]
RankingPeriodType = Literal["daily", "weekly", "monthly", "all_time"]
ReviewStatus = Literal["pending", "approved", "needs_review", "rejected"]
MarkerPosition = Literal["aboveBar", "belowBar", "inBar"]
MarkerShape = Literal["circle", "square", "arrowUp", "arrowDown"]


class PatternResponse(BaseModel):
    id: str
    slug: str
    name: str
    question_count: int = 0
    description: str | None = None
    definition: dict | None = None


class PatternMarker(BaseModel):
    time: str
    label: str
    position: MarkerPosition = "aboveBar"
    shape: MarkerShape = "circle"
    color: str = "#facc15"


class QuestionResponse(BaseModel):
    id: str
    pattern: PatternResponse
    difficulty: str
    difficulty_label: str
    market_regime: str
    timeframe: str = "1d"
    base_date: str
    chart_data: list[dict]
    hidden_candles_count: int = 5
    answer_options: list[AnswerDirection] = ["up", "sideways", "down"]
    public_accuracy: float | None = None
    pattern_score: float | None = None
    is_favorited: bool = False
    pattern_evidence: list[str] = []
    pattern_score_breakdown: dict | None = None
    pattern_markers: list[PatternMarker] = []
    is_synthetic: bool = True
    source_name: str | None = None
    source_url: str | None = None
    source_symbol: str | None = None
    source_exchange: str | None = None
    source_date_range: str | None = None


class QuestionListItem(BaseModel):
    id: str
    pattern: PatternResponse
    difficulty: str
    difficulty_label: str
    market_regime: str
    timeframe: str = "1d"
    base_date: str
    public_accuracy: float | None = None
    pattern_score: float | None = None
    total_answers: int = 0
    is_favorited: bool = False
    review_status: ReviewStatus = "pending"
    is_synthetic: bool = True
    source_symbol: str | None = None
    source_exchange: str | None = None


class AnswerSubmit(BaseModel):
    selected_answer: AnswerDirection
    confidence: int | None = Field(default=None, ge=0, le=100)
    reason_tags: list[str] = []
    answer_duration_ms: int | None = Field(default=None, ge=0)
    is_retry: bool = False
    session_id: UUID | None = None


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
    timeframe: str = "1d"
    selected_answer: AnswerDirection
    correct_answer: AnswerDirection
    is_correct: bool
    actual_next_candles: list[dict]
    ai_explanation: str | None
    pattern_evidence: list[str] = []
    pattern_score: float | None = None
    pattern_score_breakdown: dict | None = None
    pattern_markers: list[PatternMarker] = []
    is_synthetic: bool = True
    source_name: str | None = None
    source_url: str | None = None
    source_symbol: str | None = None
    source_exchange: str | None = None
    source_date_range: str | None = None
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


class SubscriptionResponse(BaseModel):
    plan: str
    status: str
    daily_question_limit: int
    solved_today: int
    remaining_today: int
    streak_days: int


class FavoriteQuestionItem(BaseModel):
    id: str
    question: QuestionListItem
    created_at: str


class FavoritesResponse(BaseModel):
    items: list[FavoriteQuestionItem]
    total: int


class FavoriteToggleResponse(BaseModel):
    question_id: str
    is_favorited: bool


class TrainingSessionSummary(BaseModel):
    session_id: str
    pattern: PatternResponse
    started_at: str
    last_answered_at: str
    solved_count: int
    correct_count: int
    accuracy: float


class TrainingSessionsResponse(BaseModel):
    items: list[TrainingSessionSummary]
    total: int
    limit: int


class TrainingSessionDetailResponse(BaseModel):
    session: TrainingSessionSummary
    answers: list[AnswerResultResponse]


class AiReportResponse(BaseModel):
    id: str
    status: str
    period_start: str
    period_end: str
    answer_count: int
    overall_score: int | None
    percentile: float | None
    pattern_accuracy: dict | None
    trait_scores: dict | None
    summary: str | None
    recommendations: list[dict] | None
    model_name: str | None
    created_at: str


class AiReportGenerateResponse(BaseModel):
    report: AiReportResponse


class ReviewQuestionItem(QuestionResponse):
    correct_answer: AnswerDirection
    actual_next_candles: list[dict]
    review_status: ReviewStatus
    review_note: str
    total_answers: int


class ReviewQuestionsResponse(BaseModel):
    items: list[ReviewQuestionItem]
    total: int
    limit: int
    offset: int


class ReviewDashboardItem(BaseModel):
    pattern: PatternResponse
    total_count: int
    pending_count: int
    approved_count: int
    needs_review_count: int
    rejected_count: int
    marker_warning_count: int
    playable_count: int
    approved_target: int = 10
    approved_shortage: int


class ReviewDashboardResponse(BaseModel):
    items: list[ReviewDashboardItem]
    approved_target: int = 10


class QuestionReviewUpdate(BaseModel):
    review_status: ReviewStatus | None = None
    review_note: str | None = None
    pattern_markers: list[PatternMarker] | None = None
