"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, ChevronRight } from "lucide-react";
import { CandlestickPreview } from "@/components/candlestick-preview";
import { PatternDefinitionCard } from "@/components/pattern-definition-card";
import { submitAnswer } from "@/lib/api";
import { getBrowserAccessToken } from "@/lib/browser-auth";
import type { AnswerDirection, Question } from "@/lib/types";

const answerLabels: Record<AnswerDirection, { label: string; hint: string; accent: string }> = {
  up: { label: "상승할 것 같다", hint: "확률 70% 이상", accent: "text-emerald-300" },
  sideways: { label: "횡보할 것 같다", hint: "±3% 이내", accent: "text-yellow-300" },
  down: { label: "하락할 것 같다", hint: "확률 70% 이상", accent: "text-red-300" },
};

export function TrainingSessionClient({ patternKey, questions }: { patternKey: string; questions: Question[] }) {
  const router = useRouter();
  const [sessionId] = useState(() => crypto.randomUUID());
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState<AnswerDirection | null>(null);
  const [answerIds, setAnswerIds] = useState<string[]>([]);
  const [startedAt, setStartedAt] = useState(() => performance.now());
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const question = questions[currentIndex];
  const answerOptions = useMemo(
    () => question.answerOptions.filter((option): option is AnswerDirection => option in answerLabels),
    [question.answerOptions],
  );
  const progressPercent = Math.round(((currentIndex + 1) / questions.length) * 100);

  async function handleSubmit() {
    if (!selectedAnswer || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const accessToken = await getBrowserAccessToken();
      if (!accessToken) {
        router.push(`/login?next=${encodeURIComponent(window.location.pathname + window.location.search)}`);
        return;
      }

      const result = await submitAnswer(
        question.id,
        {
          selectedAnswer,
          confidence: 70,
          reasonTags: [],
          answerDurationMs: Math.round(performance.now() - startedAt),
          isRetry: false,
          sessionId,
        },
        accessToken,
      );

      const nextAnswerIds = [...answerIds, result.answerId];
      if (currentIndex >= questions.length - 1) {
        const query = new URLSearchParams({
          answers: nextAnswerIds.join(","),
          session_id: sessionId,
        });
        router.push(`/training/${encodeURIComponent(patternKey)}/summary?${query.toString()}`);
        return;
      }

      setAnswerIds(nextAnswerIds);
      setCurrentIndex((value) => value + 1);
      setSelectedAnswer(null);
      setStartedAt(performance.now());
      setIsSubmitting(false);
    } catch {
      setError("답안 제출에 실패했습니다. 로그인 상태와 백엔드 배포 주소를 확인해주세요.");
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto max-w-5xl px-4 py-5">
        <header className="mb-6 flex items-center justify-between">
          <Link href="/patterns" aria-label="패턴 목록으로 이동">
            <ArrowLeft className="size-8 text-slate-300" />
          </Link>
          <div className="text-center">
            <h1 className="text-2xl font-black">연속 훈련</h1>
            <p className="text-sm text-slate-400">{question.pattern.name}</p>
          </div>
          <div className="rounded-full border border-white/10 bg-white/8 px-4 py-2 font-bold">
            {currentIndex + 1}/{questions.length}
          </div>
        </header>

        <section className="mb-6">
          <div className="mb-3 flex items-center justify-between text-slate-300">
            <span>문제 {currentIndex + 1}</span>
            <span>{progressPercent}% 진행</span>
          </div>
          <div className="h-3 rounded-full bg-slate-800">
            <div className="h-3 rounded-full bg-gradient-to-r from-purple-500 to-cyan-400" style={{ width: `${progressPercent}%` }} />
          </div>
        </section>

        <section className="mb-6">
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <span className="rounded-full border border-fuchsia-400/70 bg-fuchsia-500/20 px-4 py-1 font-bold text-fuchsia-200">
              {question.difficultyLabel}
            </span>
            <span className="font-bold">패턴: {question.pattern.name}</span>
            <span className="text-slate-400">기준일 {question.baseDate}</span>
          </div>
          <h2 className="text-3xl font-black">
            다음 <span className="text-orange-300">5봉</span>은 어떻게 될까?
          </h2>
          <p className="mt-3 text-slate-400">과거 차트를 보고 다음 5개의 캔들 방향을 선택하세요.</p>
        </section>

        <div className="mb-6">
          <PatternDefinitionCard pattern={question.pattern} evidence={question.patternEvidence} score={question.patternScore} compact />
        </div>

        <CandlestickPreview candles={question.chartData} />

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
            className="mt-6 flex w-full items-center justify-center gap-2 rounded-2xl bg-cyan-400 py-5 text-xl font-black text-slate-950 transition enabled:hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-50"
            type="button"
            disabled={!selectedAnswer || isSubmitting}
            onClick={handleSubmit}
          >
            {isSubmitting ? "제출 중..." : currentIndex >= questions.length - 1 ? "결과 요약 보기" : "제출하고 다음 문제"}
            {!isSubmitting ? <ChevronRight className="size-6" /> : null}
          </button>
          {error ? <p className="mt-3 text-sm text-red-300">{error}</p> : null}
        </section>
      </div>
    </main>
  );
}
