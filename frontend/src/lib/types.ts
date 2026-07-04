export type AnswerDirection = "up" | "sideways" | "down";

export type Pattern = {
  id: string;
  slug: string;
  name: string;
  questionCount: number;
  description: string | null;
  definition: PatternDefinition | null;
};

export type PatternDefinition = {
  summary?: string;
  structure?: string[];
  confirmation?: string[];
  invalidation?: string[];
  confusingWith?: string[];
  scorecard?: PatternScorecard;
};

export type PatternScorecard = {
  maxScore: number;
  primaryThreshold: number;
  highConfidenceThreshold?: number;
  interpretation: string[];
  criteria: PatternScoreCriterion[];
  deductions: PatternScoreDeduction[];
};

export type PatternScoreCriterion = {
  key: string;
  label: string;
  maxPoints: number;
  description: string;
};

export type PatternScoreDeduction = {
  label: string;
  points: number;
};

export type Candle = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ma10?: number;
  ma20?: number;
  ma30?: number;
  ma40?: number;
  ma50?: number;
  ma150?: number;
  ma200?: number;
};

export type Question = {
  id: string;
  pattern: Pattern;
  difficulty: "easy" | "medium" | "hard";
  difficultyLabel: string;
  marketRegime: "bull" | "sideways" | "bear" | "volatile";
  timeframe: string;
  baseDate: string;
  chartData: Candle[];
  answerOptions: AnswerDirection[];
  publicAccuracy: number;
  patternScore: number | null;
  isFavorited: boolean;
  patternEvidence: string[];
  patternScoreBreakdown: Record<string, number> | null;
  isSynthetic: boolean;
  sourceName: string | null;
  sourceUrl: string | null;
  sourceSymbol: string | null;
  sourceExchange: string | null;
  sourceDateRange: string | null;
};

export type QuestionListItem = Omit<Question, "chartData" | "answerOptions" | "patternEvidence"> & {
  totalAnswers: number;
};

export type AnswerSubmitPayload = {
  selectedAnswer: AnswerDirection;
  confidence?: number;
  reasonTags: string[];
  answerDurationMs?: number;
  isRetry: boolean;
  sessionId?: string;
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
  timeframe: string;
  actualNextCandles: Candle[];
  aiExplanation: string | null;
  patternEvidence: string[];
  patternScore: number | null;
  patternScoreBreakdown: Record<string, number> | null;
  isSynthetic: boolean;
  sourceName: string | null;
  sourceUrl: string | null;
  sourceSymbol: string | null;
  sourceExchange: string | null;
  sourceDateRange: string | null;
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

export type Subscription = {
  plan: "free" | "premium" | "b2b" | string;
  status: "active" | "trialing" | "past_due" | "canceled" | string;
  dailyQuestionLimit: number;
  solvedToday: number;
  remainingToday: number;
  streakDays: number;
};

export type FavoriteQuestionItem = {
  id: string;
  question: QuestionListItem;
  createdAt: string;
};

export type FavoritesResponse = {
  items: FavoriteQuestionItem[];
  total: number;
};

export type FavoriteToggleResponse = {
  questionId: string;
  isFavorited: boolean;
};

export type AiReportRecommendation = {
  title: string;
  description: string;
  href: string;
};

export type AiReport = {
  id: string;
  status: string;
  periodStart: string;
  periodEnd: string;
  answerCount: number;
  overallScore: number | null;
  percentile: number | null;
  patternAccuracy: Record<string, { name: string; solved_count: number; correct_count: number; accuracy: number }> | null;
  traitScores: Record<string, number> | null;
  summary: string | null;
  recommendations: AiReportRecommendation[] | null;
  modelName: string | null;
  createdAt: string;
};

export type AiReportGenerateResponse = {
  report: AiReport;
};

export type TrainingSessionSummary = {
  sessionId: string;
  pattern: Pattern;
  startedAt: string;
  lastAnsweredAt: string;
  solvedCount: number;
  correctCount: number;
  accuracy: number;
};

export type TrainingSessionsResponse = {
  items: TrainingSessionSummary[];
  total: number;
  limit: number;
};

export type TrainingSessionDetail = {
  session: TrainingSessionSummary;
  answers: AnswerResult[];
};
