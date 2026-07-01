"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { AnswerDirection, Question } from "@/lib/types";
import { submitAnswer } from "@/lib/api";

const answerLabels: Record<AnswerDirection, { label: string; hint: string; accent: string }> = {
  up: { label: "상승할 것 같다", hint: "확률 70% 이상", accent: "text-emerald-300" },
  sideways: { label: "횡보할 것 같다", hint: "±3% 이내", accent: "text-yellow-300" },
  down: { label: "하락할 것 같다", hint: "확률 70% 이상", accent: "text-red-300" },
};

export function PlayClient({ question, isRetry = false }: { question: Question; isRetry?: boolean }) {
  const router = useRouter();
  const [selectedAnswer, setSelectedAnswer] = useState<AnswerDirection | null>(null);
  const [startedAt] = useState(() => performance.now());
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const answerOptions = useMemo(
    () => question.answerOptions.filter((option): option is AnswerDirection => option in answerLabels),
    [question.answerOptions],
  );

  async function handleSubmit() {
    if (!selectedAnswer || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const result = await submitAnswer(question.id, {
        selectedAnswer,
        confidence: 70,
        reasonTags: [],
        answerDurationMs: Math.round(performance.now() - startedAt),
        isRetry,
      });
      router.push(`/result/${result.answerId}`);
    } catch {
      setError("답안 제출에 실패했습니다. 백엔드 서버와 DATABASE_URL 설정을 확인해주세요.");
      setIsSubmitting(false);
    }
  }

  return (
    <section className="mt-6">
      <p className="mb-3 text-slate-300">하나를 선택하세요</p>
      <div className="grid gap-4 sm:grid-cols-3">
        {answerOptions.map((answer) => {
          const meta = answerLabels[answer];
          const active = selectedAnswer === answer;
          return (
            <button
              key={answer}
              className={`rounded-2xl border p-6 text-left transition ${
                active ? "border-cyan-300 bg-cyan-400/10" : "border-white/10 bg-white/8 hover:border-cyan-300/60"
              }`}
              type="button"
              onClick={() => setSelectedAnswer(answer)}
            >
              <p className={`text-xl font-black ${meta.accent}`}>{meta.label}</p>
              <p className="mt-1 text-slate-400">{meta.hint}</p>
            </button>
          );
        })}
      </div>
      <button
        className="mt-6 block w-full rounded-2xl bg-slate-800 py-5 text-center text-xl font-black text-slate-300 transition enabled:hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
        type="button"
        disabled={!selectedAnswer || isSubmitting}
        onClick={handleSubmit}
      >
        {isSubmitting ? "제출 중..." : isRetry ? "복습 답안 제출하기" : "정답 제출하기"}
      </button>
      {error ? <p className="mt-3 text-sm text-red-300">{error}</p> : null}
    </section>
  );
}
