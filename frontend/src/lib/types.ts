export type AnswerDirection = "up" | "sideways" | "down";

export type Pattern = {
  id: string;
  slug: string;
  name: string;
  questionCount: number;
};

export type Candle = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ma20: number;
};

export type Question = {
  id: string;
  pattern: Pattern;
  difficulty: "easy" | "medium" | "hard";
  difficultyLabel: string;
  marketRegime: "bull" | "sideways" | "bear" | "volatile";
  baseDate: string;
  chartData: Candle[];
  answerOptions: AnswerDirection[];
  publicAccuracy: number;
};

export type AnswerSubmitPayload = {
  selectedAnswer: AnswerDirection;
  confidence?: number;
  reasonTags: string[];
  answerDurationMs?: number;
  isRetry: boolean;
};

export type AnswerSubmitResult = {
  answerId: string;
  questionId: string;
  selectedAnswer: AnswerDirection;
  correctAnswer: AnswerDirection;
  isCorrect: boolean;
};

export type AnswerResult = AnswerSubmitResult & {
  actualNextCandles: Candle[];
  aiExplanation: string | null;
  choiceDistribution: Record<AnswerDirection, number>;
};
