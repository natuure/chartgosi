import type {
  AnswerResult,
  AnswerSubmitPayload,
  AnswerSubmitResult,
  AiReport,
  AiReportGenerateResponse,
  FavoriteQuestionItem,
  FavoritesResponse,
  FavoriteToggleResponse,
  MyRanking,
  MyStats,
  Pattern,
  PatternDefinition,
  PatternMarker,
  RankingItem,
  RankingPeriodType,
  RankingsResponse,
  Question,
  QuestionListItem,
  QuestionReviewUpdate,
  ReviewDashboardResponse,
  ReviewQuestion,
  ReviewQuestionsResponse,
  ReviewStatus,
  Subscription,
  TrainingSessionDetail,
  TrainingSessionsResponse,
  TrainingSessionSummary,
  WrongNoteDetail,
  WrongNoteItem,
  WrongNotesResponse,
} from "./types";

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1").replace(/\/+$/, "");

type ApiRequestOptions = RequestInit & {
  accessToken?: string | null;
};

export class ApiRequestError extends Error {
  status: number;
  url: string;
  body: string;

  constructor(status: number, url: string, body: string) {
    super(`API request failed: ${status} ${url}${body ? ` - ${body}` : ""}`);
    this.name = "ApiRequestError";
    this.status = status;
    this.url = url;
    this.body = body;
  }
}

function apiHeaders(init?: ApiRequestOptions): HeadersInit {
  return {
    "Content-Type": "application/json",
    ...(init?.accessToken ? { Authorization: `Bearer ${init.accessToken}` } : {}),
    ...init?.headers,
  };
}

function toRequestInit(init?: ApiRequestOptions): RequestInit {
  if (!init) {
    return {};
  }
  const requestInit = { ...init };
  delete requestInit.accessToken;
  return requestInit;
}

export async function apiGet<T>(path: string, init?: ApiRequestOptions): Promise<T> {
  const requestInit = toRequestInit(init);
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...requestInit,
    cache: "no-store",
    headers: apiHeaders(init),
  });

  if (!response.ok) {
    throw new ApiRequestError(response.status, url, await response.text());
  }

  return response.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown, init?: ApiRequestOptions): Promise<T> {
  const requestInit = toRequestInit(init);
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    ...requestInit,
    method: "POST",
    headers: apiHeaders(init),
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new ApiRequestError(response.status, url, await response.text());
  }

  return response.json() as Promise<T>;
}

export async function apiPatch<T>(path: string, body?: unknown, init?: ApiRequestOptions): Promise<T> {
  const requestInit = toRequestInit(init);
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    ...requestInit,
    method: "PATCH",
    headers: apiHeaders(init),
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (!response.ok) {
    throw new ApiRequestError(response.status, url, await response.text());
  }

  return response.json() as Promise<T>;
}

export async function apiDelete<T>(path: string, init?: ApiRequestOptions): Promise<T> {
  const requestInit = toRequestInit(init);
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    ...requestInit,
    method: "DELETE",
    headers: apiHeaders(init),
  });

  if (!response.ok) {
    throw new ApiRequestError(response.status, url, await response.text());
  }

  return response.json() as Promise<T>;
}

type ApiPattern = {
  id: string;
  slug: string;
  name: string;
  question_count: number;
  description: string | null;
  definition: ApiPatternDefinition | null;
};

type ApiPatternDefinition = {
  summary?: string;
  structure?: string[];
  confirmation?: string[];
  invalidation?: string[];
  confusing_with?: string[];
  scorecard?: {
    max_score: number;
    primary_threshold: number;
    high_confidence_threshold?: number;
    interpretation?: string[];
    criteria?: Array<{
      key: string;
      label: string;
      max_points: number;
      description: string;
    }>;
    deductions?: Array<{
      label: string;
      points: number;
    }>;
  };
};

type ApiQuestion = {
  id: string;
  pattern: ApiPattern;
  difficulty: "easy" | "medium" | "hard";
  difficulty_label: string;
  market_regime: "bull" | "sideways" | "bear" | "volatile";
  timeframe: string;
  base_date: string;
  chart_data: Question["chartData"];
  answer_options: Question["answerOptions"];
  public_accuracy: number | null;
  pattern_score: number | null;
  is_favorited: boolean;
  pattern_evidence: string[];
  pattern_score_breakdown: Record<string, number> | null;
  pattern_markers: PatternMarker[];
  is_synthetic: boolean;
  source_name: string | null;
  source_url: string | null;
  source_symbol: string | null;
  source_exchange: string | null;
  source_date_range: string | null;
};

type ApiQuestionListItem = Omit<ApiQuestion, "chart_data" | "answer_options" | "pattern_evidence" | "pattern_markers"> & {
  total_answers: number;
  review_status: ReviewStatus;
};

type ApiAnswerSubmitResult = {
  answer_id: string;
  question_id: string;
  selected_answer: AnswerSubmitResult["selectedAnswer"];
  correct_answer: AnswerSubmitResult["correctAnswer"];
  is_correct: boolean;
};

type ApiAnswerResult = ApiAnswerSubmitResult & {
  pattern: ApiPattern;
  timeframe: string;
  actual_next_candles: AnswerResult["actualNextCandles"];
  ai_explanation: string | null;
  pattern_evidence: string[];
  pattern_score: number | null;
  pattern_score_breakdown: Record<string, number> | null;
  pattern_markers: PatternMarker[];
  is_synthetic: boolean;
  source_name: string | null;
  source_url: string | null;
  source_symbol: string | null;
  source_exchange: string | null;
  source_date_range: string | null;
  choice_distribution: Record<string, number>;
};

type ApiWrongNoteItem = {
  answer_id: string;
  question_id: string;
  pattern: ApiPattern;
  difficulty: WrongNoteItem["difficulty"];
  difficulty_label: string;
  base_date: string;
  selected_answer: WrongNoteItem["selectedAnswer"];
  correct_answer: WrongNoteItem["correctAnswer"];
  created_at: string;
  viewed_ai_explanation: boolean;
  ai_explanation: string | null;
};

type ApiWrongNotesResponse = {
  items: ApiWrongNoteItem[];
  total: number;
  limit: number;
  offset: number;
};

type ApiWrongNoteDetail = ApiWrongNoteItem & {
  actual_next_candles: WrongNoteDetail["actualNextCandles"];
};

type ApiPatternStats = {
  pattern: ApiPattern;
  solved_count: number;
  correct_count: number;
  accuracy: number;
};

type ApiMyStats = {
  solved_count: number;
  correct_count: number;
  wrong_count: number;
  accuracy: number;
  average_duration_ms: number | null;
  pattern_stats: ApiPatternStats[];
};

type ApiRankingItem = {
  rank: number;
  user_id: string;
  nickname: string;
  score: number;
  accuracy: number;
  solved_count: number;
  correct_count: number;
};

type ApiRankingsResponse = {
  period_type: RankingPeriodType;
  items: ApiRankingItem[];
};

type ApiMyRanking = Omit<ApiRankingItem, "rank"> & {
  period_type: RankingPeriodType;
  rank: number | null;
};

type ApiExplanationViewed = {
  answer_id: string;
  viewed_ai_explanation: boolean;
};

type ApiSubscription = {
  plan: Subscription["plan"];
  status: Subscription["status"];
  daily_question_limit: number;
  solved_today: number;
  remaining_today: number;
  streak_days: number;
};

type ApiFavoriteQuestionItem = {
  id: string;
  question: ApiQuestionListItem;
  created_at: string;
};

type ApiFavoritesResponse = {
  items: ApiFavoriteQuestionItem[];
  total: number;
};

type ApiFavoriteToggleResponse = {
  question_id: string;
  is_favorited: boolean;
};

type ApiAiReport = {
  id: string;
  status: string;
  period_start: string;
  period_end: string;
  answer_count: number;
  overall_score: number | null;
  percentile: number | null;
  pattern_accuracy: AiReport["patternAccuracy"];
  trait_scores: AiReport["traitScores"];
  summary: string | null;
  recommendations: AiReport["recommendations"];
  model_name: string | null;
  created_at: string;
};

type ApiAiReportGenerateResponse = {
  report: ApiAiReport;
};

type ApiTrainingSessionSummary = {
  session_id: string;
  pattern: ApiPattern;
  started_at: string;
  last_answered_at: string;
  solved_count: number;
  correct_count: number;
  accuracy: number;
};

type ApiTrainingSessionsResponse = {
  items: ApiTrainingSessionSummary[];
  total: number;
  limit: number;
};

type ApiTrainingSessionDetail = {
  session: ApiTrainingSessionSummary;
  answers: ApiAnswerResult[];
};

type ApiReviewQuestion = ApiQuestion & {
  correct_answer: AnswerResult["correctAnswer"];
  actual_next_candles: AnswerResult["actualNextCandles"];
  review_status: ReviewStatus;
  review_note: string;
  total_answers: number;
};

type ApiReviewQuestionsResponse = {
  items: ApiReviewQuestion[];
  total: number;
  limit: number;
  offset: number;
};

type ApiReviewDashboardItem = {
  pattern: ApiPattern;
  total_count: number;
  pending_count: number;
  approved_count: number;
  needs_review_count: number;
  rejected_count: number;
  marker_warning_count: number;
  playable_count: number;
  approved_target: number;
  approved_shortage: number;
};

type ApiReviewDashboardResponse = {
  items: ApiReviewDashboardItem[];
  approved_target: number;
};

export async function getPatterns(): Promise<Pattern[]> {
  const patterns = await apiGet<ApiPattern[]>("/patterns");
  return patterns.map(toPattern);
}

export async function getTodayQuestion(patternSlug?: string, accessToken?: string | null): Promise<Question> {
  const query = patternSlug ? `?pattern_slug=${encodeURIComponent(patternSlug)}` : "";
  return toQuestion(await apiGet<ApiQuestion>(`/questions/today${query}`, { accessToken }));
}

export async function getQuestion(questionId: string, accessToken?: string | null): Promise<Question> {
  return toQuestion(await apiGet<ApiQuestion>(`/questions/${questionId}`, { accessToken }));
}

export async function submitAnswer(questionId: string, payload: AnswerSubmitPayload, accessToken?: string | null): Promise<AnswerSubmitResult> {
  const result = await apiPost<ApiAnswerSubmitResult>(`/questions/${questionId}/answers`, {
    selected_answer: payload.selectedAnswer,
    confidence: payload.confidence,
    reason_tags: payload.reasonTags,
    answer_duration_ms: payload.answerDurationMs,
    is_retry: payload.isRetry,
    session_id: payload.sessionId,
  }, { accessToken });
  return toAnswerSubmitResult(result);
}

export async function getAnswerResult(answerId: string, accessToken?: string | null): Promise<AnswerResult> {
  const result = await apiGet<ApiAnswerResult>(`/answers/${answerId}/result`, { accessToken });
  return toAnswerResult(result);
}

export async function markAnswerExplanationViewed(answerId: string, accessToken?: string | null): Promise<boolean> {
  const response = await apiPatch<ApiExplanationViewed>(`/answers/${answerId}/explanation-viewed`, undefined, { accessToken });
  return response.viewed_ai_explanation;
}

export async function getWrongNotes(limit = 30, offset = 0, accessToken?: string | null): Promise<WrongNotesResponse> {
  const response = await apiGet<ApiWrongNotesResponse>(`/wrong-notes?limit=${limit}&offset=${offset}`, { accessToken });
  return {
    items: response.items.map(toWrongNoteItem),
    total: response.total,
    limit: response.limit,
    offset: response.offset,
  };
}

export async function getWrongNote(answerId: string, accessToken?: string | null): Promise<WrongNoteDetail> {
  const response = await apiGet<ApiWrongNoteDetail>(`/wrong-notes/${answerId}`, { accessToken });
  return {
    ...toWrongNoteItem(response),
    actualNextCandles: response.actual_next_candles,
  };
}

export async function getPatternQuestions(patternKey: string, accessToken?: string | null): Promise<QuestionListItem[]> {
  const questions = await apiGet<ApiQuestionListItem[]>(`/patterns/${encodeURIComponent(patternKey)}/questions`, { accessToken });
  return questions.map(toQuestionListItem);
}

export async function getPatternSession(patternKey: string, limit = 5, accessToken?: string | null): Promise<Question[]> {
  const questions = await apiGet<ApiQuestion[]>(
    `/patterns/${encodeURIComponent(patternKey)}/session?limit=${limit}`,
    { accessToken },
  );
  return questions.map(toQuestion);
}

export async function getMyStats(accessToken?: string | null): Promise<MyStats> {
  const response = await apiGet<ApiMyStats>("/stats/me", { accessToken });
  return {
    solvedCount: response.solved_count,
    correctCount: response.correct_count,
    wrongCount: response.wrong_count,
    accuracy: response.accuracy,
    averageDurationMs: response.average_duration_ms,
    patternStats: response.pattern_stats.map((item) => ({
      pattern: toPattern(item.pattern),
      solvedCount: item.solved_count,
      correctCount: item.correct_count,
      accuracy: item.accuracy,
    })),
  };
}

export async function getRankings(periodType: RankingPeriodType = "weekly"): Promise<RankingsResponse> {
  const response = await apiGet<ApiRankingsResponse>(`/rankings?period_type=${periodType}`);
  return {
    periodType: response.period_type,
    items: response.items.map(toRankingItem),
  };
}

export async function getMyRanking(periodType: RankingPeriodType = "weekly", accessToken?: string | null): Promise<MyRanking> {
  const response = await apiGet<ApiMyRanking>(`/rankings/me?period_type=${periodType}`, { accessToken });
  return toMyRanking(response);
}

export async function getSubscription(accessToken?: string | null): Promise<Subscription> {
  const response = await apiGet<ApiSubscription>("/subscriptions/me", { accessToken });
  return {
    plan: response.plan,
    status: response.status,
    dailyQuestionLimit: response.daily_question_limit,
    solvedToday: response.solved_today,
    remainingToday: response.remaining_today,
    streakDays: response.streak_days,
  };
}

export async function getFavorites(accessToken?: string | null): Promise<FavoritesResponse> {
  const response = await apiGet<ApiFavoritesResponse>("/favorites", { accessToken });
  return {
    items: response.items.map(toFavoriteQuestionItem),
    total: response.total,
  };
}

export async function addFavoriteQuestion(questionId: string, accessToken?: string | null): Promise<FavoriteToggleResponse> {
  const response = await apiPost<ApiFavoriteToggleResponse>(`/questions/${questionId}/favorite`, {}, { accessToken });
  return toFavoriteToggleResponse(response);
}

export async function removeFavoriteQuestion(questionId: string, accessToken?: string | null): Promise<FavoriteToggleResponse> {
  const response = await apiDelete<ApiFavoriteToggleResponse>(`/questions/${questionId}/favorite`, { accessToken });
  return toFavoriteToggleResponse(response);
}

export async function getLatestAiReport(accessToken?: string | null): Promise<AiReport> {
  return toAiReport(await apiGet<ApiAiReport>("/ai-reports/latest", { accessToken }));
}

export async function generateAiReport(accessToken?: string | null): Promise<AiReportGenerateResponse> {
  const response = await apiPost<ApiAiReportGenerateResponse>("/ai-reports/generate", {}, { accessToken });
  return { report: toAiReport(response.report) };
}

export async function getRecentTrainingSessions(limit = 20, accessToken?: string | null): Promise<TrainingSessionsResponse> {
  const response = await apiGet<ApiTrainingSessionsResponse>(`/training-sessions/recent?limit=${limit}`, { accessToken });
  return {
    items: response.items.map(toTrainingSessionSummary),
    total: response.total,
    limit: response.limit,
  };
}

export async function getTrainingSessionDetail(sessionId: string, accessToken?: string | null): Promise<TrainingSessionDetail> {
  const response = await apiGet<ApiTrainingSessionDetail>(`/training-sessions/${encodeURIComponent(sessionId)}`, { accessToken });
  return {
    session: toTrainingSessionSummary(response.session),
    answers: response.answers.map(toAnswerResult),
  };
}

export async function getReviewQuestions(
  params: { patternSlug?: string; reviewStatus?: ReviewStatus; limit?: number; offset?: number } = {},
  accessToken?: string | null,
): Promise<ReviewQuestionsResponse> {
  const query = new URLSearchParams();
  if (params.patternSlug) {
    query.set("pattern_slug", params.patternSlug);
  }
  if (params.reviewStatus) {
    query.set("review_status", params.reviewStatus);
  }
  query.set("limit", String(params.limit ?? 20));
  query.set("offset", String(params.offset ?? 0));
  const response = await apiGet<ApiReviewQuestionsResponse>(`/review/questions?${query.toString()}`, { accessToken });
  return {
    items: response.items.map(toReviewQuestion),
    total: response.total,
    limit: response.limit,
    offset: response.offset,
  };
}

export async function getReviewDashboard(accessToken?: string | null): Promise<ReviewDashboardResponse> {
  const response = await apiGet<ApiReviewDashboardResponse>("/review/dashboard", { accessToken });
  return {
    items: response.items.map((item) => ({
      pattern: toPattern(item.pattern),
      totalCount: item.total_count,
      pendingCount: item.pending_count,
      approvedCount: item.approved_count,
      needsReviewCount: item.needs_review_count,
      rejectedCount: item.rejected_count,
      markerWarningCount: item.marker_warning_count,
      playableCount: item.playable_count,
      approvedTarget: item.approved_target,
      approvedShortage: item.approved_shortage,
    })),
    approvedTarget: response.approved_target,
  };
}

export async function updateQuestionReview(
  questionId: string,
  payload: QuestionReviewUpdate,
  accessToken?: string | null,
): Promise<ReviewQuestion> {
  const response = await apiPatch<ApiReviewQuestion>(`/review/questions/${questionId}`, {
    review_status: payload.reviewStatus,
    review_note: payload.reviewNote,
    pattern_markers: payload.patternMarkers,
  }, { accessToken });
  return toReviewQuestion(response);
}

function toPattern(pattern: ApiPattern): Pattern {
  return {
    id: pattern.id,
    slug: pattern.slug,
    name: pattern.name,
    questionCount: pattern.question_count,
    description: pattern.description,
    definition: toPatternDefinition(pattern.definition),
  };
}

function toPatternDefinition(definition: ApiPatternDefinition | null): PatternDefinition | null {
  if (!definition) {
    return null;
  }
  return {
    summary: definition.summary,
    structure: definition.structure ?? [],
    confirmation: definition.confirmation ?? [],
    invalidation: definition.invalidation ?? [],
    confusingWith: definition.confusing_with ?? [],
    scorecard: definition.scorecard
      ? {
          maxScore: definition.scorecard.max_score,
          primaryThreshold: definition.scorecard.primary_threshold,
          highConfidenceThreshold: definition.scorecard.high_confidence_threshold,
          interpretation: definition.scorecard.interpretation ?? [],
          criteria: (definition.scorecard.criteria ?? []).map((item) => ({
            key: item.key,
            label: item.label,
            maxPoints: item.max_points,
            description: item.description,
          })),
          deductions: (definition.scorecard.deductions ?? []).map((item) => ({
            label: item.label,
            points: item.points,
          })),
        }
      : undefined,
  };
}

function toQuestion(question: ApiQuestion): Question {
  return {
    id: question.id,
    pattern: toPattern(question.pattern),
    difficulty: question.difficulty,
    difficultyLabel: question.difficulty_label,
    marketRegime: question.market_regime,
    timeframe: question.timeframe ?? "1d",
    baseDate: question.base_date,
    chartData: question.chart_data,
    answerOptions: question.answer_options,
    publicAccuracy: question.public_accuracy ?? 0,
    patternScore: question.pattern_score,
    isFavorited: question.is_favorited,
    patternEvidence: question.pattern_evidence ?? [],
    patternScoreBreakdown: question.pattern_score_breakdown ?? null,
    patternMarkers: question.pattern_markers ?? [],
    isSynthetic: question.is_synthetic ?? true,
    sourceName: question.source_name ?? null,
    sourceUrl: question.source_url ?? null,
    sourceSymbol: question.source_symbol ?? null,
    sourceExchange: question.source_exchange ?? null,
    sourceDateRange: question.source_date_range ?? null,
  };
}

function toQuestionListItem(question: ApiQuestionListItem): QuestionListItem {
  return {
    id: question.id,
    pattern: toPattern(question.pattern),
    difficulty: question.difficulty,
    difficultyLabel: question.difficulty_label,
    marketRegime: question.market_regime,
    timeframe: question.timeframe ?? "1d",
    baseDate: question.base_date,
    publicAccuracy: question.public_accuracy ?? 0,
    patternScore: question.pattern_score,
    totalAnswers: question.total_answers,
    reviewStatus: question.review_status ?? "pending",
    isFavorited: question.is_favorited,
    patternScoreBreakdown: question.pattern_score_breakdown ?? null,
    isSynthetic: question.is_synthetic ?? true,
    sourceName: question.source_name ?? null,
    sourceUrl: question.source_url ?? null,
    sourceSymbol: question.source_symbol ?? null,
    sourceExchange: question.source_exchange ?? null,
    sourceDateRange: question.source_date_range ?? null,
  };
}

function toFavoriteQuestionItem(item: ApiFavoriteQuestionItem): FavoriteQuestionItem {
  return {
    id: item.id,
    question: toQuestionListItem(item.question),
    createdAt: item.created_at,
  };
}

function toFavoriteToggleResponse(item: ApiFavoriteToggleResponse): FavoriteToggleResponse {
  return {
    questionId: item.question_id,
    isFavorited: item.is_favorited,
  };
}

function toAiReport(report: ApiAiReport): AiReport {
  return {
    id: report.id,
    status: report.status,
    periodStart: report.period_start,
    periodEnd: report.period_end,
    answerCount: report.answer_count,
    overallScore: report.overall_score,
    percentile: report.percentile,
    patternAccuracy: report.pattern_accuracy,
    traitScores: report.trait_scores,
    summary: report.summary,
    recommendations: report.recommendations,
    modelName: report.model_name,
    createdAt: report.created_at,
  };
}

function toAnswerResult(result: ApiAnswerResult): AnswerResult {
  return {
    ...toAnswerSubmitResult(result),
    pattern: toPattern(result.pattern),
    timeframe: result.timeframe ?? "1d",
    actualNextCandles: result.actual_next_candles,
    aiExplanation: result.ai_explanation,
    patternEvidence: result.pattern_evidence ?? [],
    patternScore: result.pattern_score,
    patternScoreBreakdown: result.pattern_score_breakdown ?? null,
    patternMarkers: result.pattern_markers ?? [],
    isSynthetic: result.is_synthetic ?? true,
    sourceName: result.source_name ?? null,
    sourceUrl: result.source_url ?? null,
    sourceSymbol: result.source_symbol ?? null,
    sourceExchange: result.source_exchange ?? null,
    sourceDateRange: result.source_date_range ?? null,
    choiceDistribution: {
      up: result.choice_distribution.up ?? 0,
      sideways: result.choice_distribution.sideways ?? 0,
      down: result.choice_distribution.down ?? 0,
    },
  };
}

function toAnswerSubmitResult(result: ApiAnswerSubmitResult): AnswerSubmitResult {
  return {
    answerId: result.answer_id,
    questionId: result.question_id,
    selectedAnswer: result.selected_answer,
    correctAnswer: result.correct_answer,
    isCorrect: result.is_correct,
  };
}

function toTrainingSessionSummary(item: ApiTrainingSessionSummary): TrainingSessionSummary {
  return {
    sessionId: item.session_id,
    pattern: toPattern(item.pattern),
    startedAt: item.started_at,
    lastAnsweredAt: item.last_answered_at,
    solvedCount: item.solved_count,
    correctCount: item.correct_count,
    accuracy: item.accuracy,
  };
}

function toReviewQuestion(question: ApiReviewQuestion): ReviewQuestion {
  return {
    ...toQuestion(question),
    correctAnswer: question.correct_answer,
    actualNextCandles: question.actual_next_candles,
    reviewStatus: question.review_status,
    reviewNote: question.review_note,
    totalAnswers: question.total_answers,
  };
}

function toWrongNoteItem(item: ApiWrongNoteItem): WrongNoteItem {
  return {
    answerId: item.answer_id,
    questionId: item.question_id,
    pattern: toPattern(item.pattern),
    difficulty: item.difficulty,
    difficultyLabel: item.difficulty_label,
    baseDate: item.base_date,
    selectedAnswer: item.selected_answer,
    correctAnswer: item.correct_answer,
    createdAt: item.created_at,
    viewedAiExplanation: item.viewed_ai_explanation,
    aiExplanation: item.ai_explanation,
  };
}

function toRankingItem(item: ApiRankingItem): RankingItem {
  return {
    rank: item.rank,
    userId: item.user_id,
    nickname: item.nickname,
    score: item.score,
    accuracy: item.accuracy,
    solvedCount: item.solved_count,
    correctCount: item.correct_count,
  };
}

function toMyRanking(item: ApiMyRanking): MyRanking {
  return {
    rank: item.rank,
    userId: item.user_id,
    nickname: item.nickname,
    score: item.score,
    accuracy: item.accuracy,
    solvedCount: item.solved_count,
    correctCount: item.correct_count,
    periodType: item.period_type,
  };
}
