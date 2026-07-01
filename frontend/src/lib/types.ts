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

export type QuestionListItem = Omit<Question, "chartData" | "answerOptions"> & {
  totalAnswers: number;
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
  pattern: Pattern;
  actualNextCandles: Candle[];
  aiExplanation: string | null;
  choiceDistribution: Record<AnswerDirection, number>;
};

export type WrongNoteItem = {
  answerId: string;
  questionId: string;
  pattern: Pattern;
  difficulty: "easy" | "medium" | "hard";
  difficultyLabel: string;
  baseDate: string;
  selectedAnswer: AnswerDirection;
  correctAnswer: AnswerDirection;
  createdAt: string;
  viewedAiExplanation: boolean;
  aiExplanation: string | null;
};

export type WrongNotesResponse = {
  items: WrongNoteItem[];
  total: number;
  limit: number;
  offset: number;
};

export type WrongNoteDetail = WrongNoteItem & {
  actualNextCandles: Candle[];
};

export type PatternStats = {
  pattern: Pattern;
  solvedCount: number;
  correctCount: number;
  accuracy: number;
};

export type MyStats = {
  solvedCount: number;
  correctCount: number;
  wrongCount: number;
  accuracy: number;
  averageDurationMs: number | null;
  patternStats: PatternStats[];
};

export type RankingPeriodType = "daily" | "weekly" | "monthly" | "all_time";

export type RankingItem = {
  rank: number;
  userId: string;
  nickname: string;
  score: number;
  accuracy: number;
  solvedCount: number;
  correctCount: number;
};

export type RankingsResponse = {
  periodType: RankingPeriodType;
  items: RankingItem[];
};

export type MyRanking = Omit<RankingItem, "rank"> & {
  periodType: RankingPeriodType;
  rank: number | null;
};
