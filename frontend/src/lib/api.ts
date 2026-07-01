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
  RankingItem,
  RankingPeriodType,
  RankingsResponse,
  Question,
  QuestionListItem,
  Subscription,
  WrongNoteDetail,
  WrongNoteItem,
  WrongNotesResponse,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function apiPatch<T>(path: string, body?: unknown, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function apiDelete<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

type ApiPattern = {
  id: string;
  slug: string;
  name: string;
  question_count: number;
};

type ApiQuestion = {
  id: string;
  pattern: ApiPattern;
  difficulty: "easy" | "medium" | "hard";
  difficulty_label: string;
  market_regime: "bull" | "sideways" | "bear" | "volatile";
  base_date: string;
  chart_data: Question["chartData"];
  answer_options: Question["answerOptions"];
  public_accuracy: number | null;
  is_favorited: boolean;
};

type ApiQuestionListItem = Omit<ApiQuestion, "chart_data" | "answer_options"> & {
  total_answers: number;
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
  actual_next_candles: AnswerResult["actualNextCandles"];
  ai_explanation: string | null;
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

export async function getPatterns(): Promise<Pattern[]> {
  const patterns = await apiGet<ApiPattern[]>("/patterns");
  return patterns.map(toPattern);
}

export async function getTodayQuestion(patternSlug?: string): Promise<Question> {
  const query = patternSlug ? `?pattern_slug=${encodeURIComponent(patternSlug)}` : "";
  return toQuestion(await apiGet<ApiQuestion>(`/questions/today${query}`));
}

export async function getQuestion(questionId: string): Promise<Question> {
  return toQuestion(await apiGet<ApiQuestion>(`/questions/${questionId}`));
}

export async function submitAnswer(questionId: string, payload: AnswerSubmitPayload): Promise<AnswerSubmitResult> {
  const result = await apiPost<ApiAnswerSubmitResult>(`/questions/${questionId}/answers`, {
    selected_answer: payload.selectedAnswer,
    confidence: payload.confidence,
    reason_tags: payload.reasonTags,
    answer_duration_ms: payload.answerDurationMs,
    is_retry: payload.isRetry,
  });
  return toAnswerSubmitResult(result);
}

export async function getAnswerResult(answerId: string): Promise<AnswerResult> {
  const result = await apiGet<ApiAnswerResult>(`/answers/${answerId}/result`);
  return {
    ...toAnswerSubmitResult(result),
    pattern: toPattern(result.pattern),
    actualNextCandles: result.actual_next_candles,
    aiExplanation: result.ai_explanation,
    choiceDistribution: {
      up: result.choice_distribution.up ?? 0,
      sideways: result.choice_distribution.sideways ?? 0,
      down: result.choice_distribution.down ?? 0,
    },
  };
}

export async function markAnswerExplanationViewed(answerId: string): Promise<boolean> {
  const response = await apiPatch<ApiExplanationViewed>(`/answers/${answerId}/explanation-viewed`);
  return response.viewed_ai_explanation;
}

export async function getWrongNotes(limit = 30, offset = 0): Promise<WrongNotesResponse> {
  const response = await apiGet<ApiWrongNotesResponse>(`/wrong-notes?limit=${limit}&offset=${offset}`);
  return {
    items: response.items.map(toWrongNoteItem),
    total: response.total,
    limit: response.limit,
    offset: response.offset,
  };
}

export async function getWrongNote(answerId: string): Promise<WrongNoteDetail> {
  const response = await apiGet<ApiWrongNoteDetail>(`/wrong-notes/${answerId}`);
  return {
    ...toWrongNoteItem(response),
    actualNextCandles: response.actual_next_candles,
  };
}

export async function getPatternQuestions(patternKey: string): Promise<QuestionListItem[]> {
  const questions = await apiGet<ApiQuestionListItem[]>(`/patterns/${encodeURIComponent(patternKey)}/questions`);
  return questions.map(toQuestionListItem);
}

export async function getMyStats(): Promise<MyStats> {
  const response = await apiGet<ApiMyStats>("/stats/me");
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

export async function getMyRanking(periodType: RankingPeriodType = "weekly"): Promise<MyRanking> {
  const response = await apiGet<ApiMyRanking>(`/rankings/me?period_type=${periodType}`);
  return toMyRanking(response);
}

export async function getSubscription(): Promise<Subscription> {
  const response = await apiGet<ApiSubscription>("/subscriptions/me");
  return {
    plan: response.plan,
    status: response.status,
    dailyQuestionLimit: response.daily_question_limit,
    solvedToday: response.solved_today,
    remainingToday: response.remaining_today,
    streakDays: response.streak_days,
  };
}

export async function getFavorites(): Promise<FavoritesResponse> {
  const response = await apiGet<ApiFavoritesResponse>("/favorites");
  return {
    items: response.items.map(toFavoriteQuestionItem),
    total: response.total,
  };
}

export async function addFavoriteQuestion(questionId: string): Promise<FavoriteToggleResponse> {
  const response = await apiPost<ApiFavoriteToggleResponse>(`/questions/${questionId}/favorite`, {});
  return toFavoriteToggleResponse(response);
}

export async function removeFavoriteQuestion(questionId: string): Promise<FavoriteToggleResponse> {
  const response = await apiDelete<ApiFavoriteToggleResponse>(`/questions/${questionId}/favorite`);
  return toFavoriteToggleResponse(response);
}

export async function getLatestAiReport(): Promise<AiReport> {
  return toAiReport(await apiGet<ApiAiReport>("/ai-reports/latest"));
}

export async function generateAiReport(): Promise<AiReportGenerateResponse> {
  const response = await apiPost<ApiAiReportGenerateResponse>("/ai-reports/generate", {});
  return { report: toAiReport(response.report) };
}

function toPattern(pattern: ApiPattern): Pattern {
  return {
    id: pattern.id,
    slug: pattern.slug,
    name: pattern.name,
    questionCount: pattern.question_count,
  };
}

function toQuestion(question: ApiQuestion): Question {
  return {
    id: question.id,
    pattern: toPattern(question.pattern),
    difficulty: question.difficulty,
    difficultyLabel: question.difficulty_label,
    marketRegime: question.market_regime,
    baseDate: question.base_date,
    chartData: question.chart_data,
    answerOptions: question.answer_options,
    publicAccuracy: question.public_accuracy ?? 0,
    isFavorited: question.is_favorited,
  };
}

function toQuestionListItem(question: ApiQuestionListItem): QuestionListItem {
  return {
    id: question.id,
    pattern: toPattern(question.pattern),
    difficulty: question.difficulty,
    difficultyLabel: question.difficulty_label,
    marketRegime: question.market_regime,
    baseDate: question.base_date,
    publicAccuracy: question.public_accuracy ?? 0,
    totalAnswers: question.total_answers,
    isFavorited: question.is_favorited,
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

function toAnswerSubmitResult(result: ApiAnswerSubmitResult): AnswerSubmitResult {
  return {
    answerId: result.answer_id,
    questionId: result.question_id,
    selectedAnswer: result.selected_answer,
    correctAnswer: result.correct_answer,
    isCorrect: result.is_correct,
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
