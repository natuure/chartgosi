import type { AnswerResult, AnswerSubmitPayload, AnswerSubmitResult, Pattern, Question } from "./types";

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
};

type ApiAnswerSubmitResult = {
  answer_id: string;
  question_id: string;
  selected_answer: AnswerSubmitResult["selectedAnswer"];
  correct_answer: AnswerSubmitResult["correctAnswer"];
  is_correct: boolean;
};

type ApiAnswerResult = ApiAnswerSubmitResult & {
  actual_next_candles: AnswerResult["actualNextCandles"];
  ai_explanation: string | null;
  choice_distribution: Record<string, number>;
};

export async function getPatterns(): Promise<Pattern[]> {
  const patterns = await apiGet<ApiPattern[]>("/patterns");
  return patterns.map(toPattern);
}

export async function getTodayQuestion(): Promise<Question> {
  return toQuestion(await apiGet<ApiQuestion>("/questions/today"));
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
    actualNextCandles: result.actual_next_candles,
    aiExplanation: result.ai_explanation,
    choiceDistribution: {
      up: result.choice_distribution.up ?? 0,
      sideways: result.choice_distribution.sideways ?? 0,
      down: result.choice_distribution.down ?? 0,
    },
  };
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
