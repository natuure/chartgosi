"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { CandlestickPreview } from "@/components/candlestick-preview";
import type { AnswerDirection, AnswerResult, Candle, Question } from "@/lib/types";
import { getAnswerResult, submitAnswer } from "@/lib/api";
import { formatApiError } from "@/lib/api-errors";
import { getBrowserAccessToken } from "@/lib/browser-auth";

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
  const [isRevealing, setIsRevealing] = useState(false);
  const [revealedCandles, setRevealedCandles] = useState<Candle[]>([]);
  const [answerResult, setAnswerResult] = useState<AnswerResult | null>(null);
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
      const accessToken = await getBrowserAccessToken();
      if (!accessToken) {
        setIsSubmitting(false);
        router.push(`/login?next=${encodeURIComponent(window.location.pathname + window.location.search)}`);
        return;
      }
      const submittedAnswer = await submitAnswer(
        question.id,
        {
          selectedAnswer,
          confidence: 70,
          reasonTags: [],
          answerDurationMs: Math.round(performance.now() - startedAt),
          isRetry,
        },
        accessToken,
      );
      const result = await getAnswerResult(submittedAnswer.answerId, accessToken);
      const nextCandles = result.actualNextCandles.slice(0, 5);
      setAnswerResult(result);
      setIsRevealing(true);
      setRevealedCandles([]);

      for (let index = 0; index < nextCandles.length; index += 1) {
        await wait(700);
        setRevealedCandles(nextCandles.slice(0, index + 1));
      }

      setIsRevealing(false);
      setIsSubmitting(false);
    } catch (error) {
      setError(formatApiError("답안 제출", error));
      setIsSubmitting(false);
      setIsRevealing(false);
    }
  }

  function handleGoToResult() {
    if (answerResult) {
      router.push(`/result/${answerResult.answerId}`);
    }
  }

  return (
    <section className="mt-6">
      <CandlestickPreview
        candles={question.chartData}
        revealedCandles={revealedCandles}
        showHiddenOverlay={!answerResult || (isRevealing && revealedCandles.length === 0)}
      />

      <p className="mb-3 mt-6 text-slate-300">하나를 선택하세요</p>
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
              disabled={Boolean(answerResult) || isSubmitting}
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
        disabled={answerResult ? isRevealing : !selectedAnswer || isSubmitting}
        onClick={answerResult ? handleGoToResult : handleSubmit}
      >
        {buttonLabel({ answerResult, isRetry, isRevealing, isSubmitting })}
      </button>
      {answerResult ? (
        <p className={answerResult.isCorrect ? "mt-3 text-sm font-bold text-emerald-300" : "mt-3 text-sm font-bold text-red-300"}>
          {answerResult.isCorrect ? "정답입니다. 다음 5봉을 차트에서 확인해보세요." : "오답입니다. 실제 다음 5봉 흐름을 차트에서 확인해보세요."}
        </p>
      ) : null}
      {error ? <p className="mt-3 text-sm text-red-300">{error}</p> : null}
    </section>
  );
}

function buttonLabel({
  answerResult,
  isRetry,
  isRevealing,
  isSubmitting,
}: {
  answerResult: AnswerResult | null;
  isRetry: boolean;
  isRevealing: boolean;
  isSubmitting: boolean;
}) {
  if (answerResult) {
    return isRevealing ? "다음 5봉 확인 중..." : "다음: 결과 화면 보기";
  }
  if (isSubmitting) {
    return "제출 중...";
  }
  return isRetry ? "복습 답안 제출하기" : "정답 제출하기";
}

function wait(ms: number) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}
