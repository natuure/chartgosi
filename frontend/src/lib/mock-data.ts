import type { Pattern, Question } from "./types";

export const patterns: Pattern[] = [
  { id: "p_cup_handle", slug: "cup-and-handle", name: "컵앤핸들", questionCount: 125 },
  { id: "p_double_bottom", slug: "double-bottom", name: "W바닥", questionCount: 118 },
  { id: "p_box_breakout", slug: "box-breakout", name: "박스권 돌파", questionCount: 132 },
  { id: "p_new_high_breakout", slug: "new-high-breakout", name: "신고가 돌파", questionCount: 110 },
  { id: "p_pullback", slug: "pullback", name: "눌림목", questionCount: 115 },
  { id: "p_triangle", slug: "triangle", name: "삼각수렴", questionCount: 103 },
  { id: "p_flag", slug: "flag", name: "플래그", questionCount: 96 },
  { id: "p_inverse_head_shoulders", slug: "inverse-head-shoulders", name: "역헤드&숄더", questionCount: 99 },
  { id: "p_ma_breakout", slug: "moving-average-breakout", name: "이평선 돌파", questionCount: 108 },
  { id: "p_volume_spike", slug: "volume-spike", name: "거래량 급증", questionCount: 124 },
];

export const sampleQuestion: Question = {
  id: "q_sample_001",
  pattern: patterns[0],
  difficulty: "medium",
  difficultyLabel: "중급",
  marketRegime: "sideways",
  baseDate: "2024-06-21",
  answerOptions: ["up", "sideways", "down"],
  publicAccuracy: 0.7,
  chartData: Array.from({ length: 56 }).map((_, index) => {
    const wave = Math.sin(index / 3.2) * 5;
    const drift = index * 0.18;
    const open = 92 + wave + drift + (index % 5) * 0.4;
    const close = open + Math.sin(index / 2) * 2.2;
    const high = Math.max(open, close) + 1.8 + (index % 3) * 0.35;
    const low = Math.min(open, close) - 1.5 - (index % 4) * 0.25;
    return {
      time: `2024-05-${String((index % 28) + 1).padStart(2, "0")}`,
      open: Number(open.toFixed(2)),
      high: Number(high.toFixed(2)),
      low: Number(low.toFixed(2)),
      close: Number(close.toFixed(2)),
      volume: 800000 + ((index * 137000) % 1200000),
      ma20: Number((94 + drift + Math.sin(index / 5) * 2).toFixed(2)),
    };
  }),
};
