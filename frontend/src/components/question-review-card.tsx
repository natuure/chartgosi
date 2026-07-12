"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { CheckCircle2, ExternalLink, Save, XCircle } from "lucide-react";
import { CandlestickPreview } from "@/components/candlestick-preview";
import { updateQuestionReview } from "@/lib/api";
import { formatApiError } from "@/lib/api-errors";
import { getBrowserAccessToken } from "@/lib/browser-auth";
import type { PatternMarker, ReviewQuestion, ReviewStatus } from "@/lib/types";

const statusLabels: Record<ReviewStatus, string> = {
  pending: "대기",
  approved: "좋음",
  needs_review: "애매함",
  rejected: "제외",
};

const statusClasses: Record<ReviewStatus, string> = {
  pending: "border-slate-400/30 bg-slate-400/10 text-slate-200",
  approved: "border-emerald-300/40 bg-emerald-400/15 text-emerald-100",
  needs_review: "border-yellow-300/40 bg-yellow-400/15 text-yellow-100",
  rejected: "border-red-300/40 bg-red-400/15 text-red-100",
};

export function QuestionReviewCard({ question }: { question: ReviewQuestion }) {
  const [reviewStatus, setReviewStatus] = useState<ReviewStatus>(question.reviewStatus);
  const [reviewNote, setReviewNote] = useState(question.reviewNote);
  const [markersText, setMarkersText] = useState(() => JSON.stringify(question.patternMarkers, null, 2));
  const [savedQuestion, setSavedQuestion] = useState(question);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const parsedMarkers = useMemo(() => {
    try {
      const value = JSON.parse(markersText) as PatternMarker[];
      return Array.isArray(value) ? value : [];
    } catch {
      return savedQuestion.patternMarkers;
    }
  }, [markersText, savedQuestion.patternMarkers]);

  async function handleSave(nextStatus = reviewStatus) {
    setIsSaving(true);
    setError(null);
    setMessage(null);

    let markers: PatternMarker[];
    try {
      const parsed = JSON.parse(markersText) as PatternMarker[];
      markers = Array.isArray(parsed) ? parsed : [];
    } catch {
      setError("마커 JSON 형식이 올바르지 않습니다.");
      setIsSaving(false);
      return;
    }

    try {
      const accessToken = await getBrowserAccessToken();
      const updated = await updateQuestionReview(
        question.id,
        {
          reviewStatus: nextStatus,
          reviewNote,
          patternMarkers: markers,
        },
        accessToken,
      );
      setSavedQuestion(updated);
      setReviewStatus(updated.reviewStatus);
      setReviewNote(updated.reviewNote);
      setMarkersText(JSON.stringify(updated.patternMarkers, null, 2));
      setMessage("검수 내용이 저장되었습니다.");
    } catch (error) {
      setError(formatApiError("검수 저장", error));
    } finally {
      setIsSaving(false);
    }
  }

  function addMarkerFromCandle(index: number, label: string, position: PatternMarker["position"], color: string) {
    const candle = savedQuestion.chartData[index];
    if (!candle) {
      return;
    }
    const nextMarkers = [
      ...parsedMarkers,
      {
        time: candle.time,
        label,
        position,
        shape: "circle" as const,
        color,
      },
    ];
    setMarkersText(JSON.stringify(nextMarkers, null, 2));
  }

  return (
    <article className="rounded-3xl border border-white/10 bg-white/8 p-5">
      <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-full border px-3 py-1 text-xs font-black ${statusClasses[reviewStatus]}`}>
              {statusLabels[reviewStatus]}
            </span>
            <span className="rounded-full border border-cyan-300/30 bg-cyan-400/10 px-3 py-1 text-xs font-bold text-cyan-100">
              {savedQuestion.pattern.name}
            </span>
            <span className="rounded-full border border-white/10 px-3 py-1 text-xs font-bold text-slate-300">
              {savedQuestion.timeframe}
            </span>
          </div>
          <h2 className="mt-3 text-2xl font-black">
            {savedQuestion.sourceSymbol ?? savedQuestion.id}
            <span className="ml-2 text-base text-slate-400">{savedQuestion.baseDate}</span>
          </h2>
          <p className="mt-2 text-sm text-slate-400">
            정답 {answerLabel(savedQuestion.correctAnswer)} · 점수 {savedQuestion.patternScore ?? "-"} · 풀이 {savedQuestion.totalAnswers}회
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href={`/play?question_id=${encodeURIComponent(savedQuestion.id)}`}
            className="inline-flex items-center gap-2 rounded-xl border border-white/10 px-4 py-2 text-sm font-bold text-slate-100 hover:border-cyan-300/60"
          >
            문제 열기 <ExternalLink className="size-4" />
          </Link>
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-xl bg-emerald-400 px-4 py-2 text-sm font-black text-slate-950 disabled:opacity-50"
            disabled={isSaving}
            onClick={() => handleSave("approved")}
          >
            <CheckCircle2 className="size-4" /> 좋음
          </button>
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-xl bg-red-400 px-4 py-2 text-sm font-black text-slate-950 disabled:opacity-50"
            disabled={isSaving}
            onClick={() => handleSave("rejected")}
          >
            <XCircle className="size-4" /> 제외
          </button>
        </div>
      </div>

      <CandlestickPreview
        candles={savedQuestion.chartData}
        timeframe={savedQuestion.timeframe}
        patternSlug={savedQuestion.pattern.slug}
        revealedCandles={savedQuestion.actualNextCandles}
        showHiddenOverlay={false}
        patternMarkers={parsedMarkers}
      />

      <section className="mt-5 grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
          <h3 className="font-black text-cyan-100">이 문제를 이렇게 본 이유</h3>
          <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-300">
            {savedQuestion.patternEvidence.map((item) => (
              <li key={item}>• {item}</li>
            ))}
          </ul>
        </div>

        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-2">
            {(["pending", "approved", "needs_review", "rejected"] as const).map((status) => (
              <button
                key={status}
                type="button"
                className={`rounded-xl border px-3 py-2 text-sm font-black ${reviewStatus === status ? statusClasses[status] : "border-white/10 bg-slate-900 text-slate-300"}`}
                onClick={() => setReviewStatus(status)}
              >
                {statusLabels[status]}
              </button>
            ))}
          </div>

          <textarea
            className="min-h-24 w-full rounded-2xl border border-white/10 bg-slate-950 p-3 text-sm text-slate-100 outline-none focus:border-cyan-300"
            placeholder="왜 좋거나 애매한지 메모하세요."
            value={reviewNote}
            onChange={(event) => setReviewNote(event.target.value)}
          />

          <div className="rounded-2xl border border-white/10 bg-slate-950 p-3">
            <div className="mb-2 flex flex-wrap gap-2">
              <button type="button" className="rounded-lg bg-cyan-400/15 px-3 py-1 text-xs font-bold text-cyan-100" onClick={() => addMarkerFromCandle(0, "시작", "belowBar", "#22c55e")}>
                시작 마커
              </button>
              <button type="button" className="rounded-lg bg-fuchsia-400/15 px-3 py-1 text-xs font-bold text-fuchsia-100" onClick={() => addMarkerFromCandle(savedQuestion.chartData.length - 1, "확정봉", "aboveBar", "#facc15")}>
                마지막 봉 마커
              </button>
            </div>
            <textarea
              className="h-44 w-full resize-y rounded-xl border border-white/10 bg-slate-900 p-3 font-mono text-xs text-slate-100 outline-none focus:border-cyan-300"
              value={markersText}
              onChange={(event) => setMarkersText(event.target.value)}
            />
            <p className="mt-2 text-xs text-slate-400">
              형식: time, label, position(aboveBar/belowBar/inBar), shape(circle/square/arrowUp/arrowDown), color
            </p>
          </div>

          <button
            type="button"
            className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-cyan-400 px-4 py-3 font-black text-slate-950 disabled:opacity-50"
            disabled={isSaving}
            onClick={() => handleSave()}
          >
            <Save className="size-5" /> {isSaving ? "저장 중..." : "검수 저장"}
          </button>
          {message ? <p className="text-sm font-bold text-emerald-300">{message}</p> : null}
          {error ? <p className="text-sm font-bold text-red-300">{error}</p> : null}
        </div>
      </section>
    </article>
  );
}

function answerLabel(answer: ReviewQuestion["correctAnswer"]) {
  if (answer === "up") {
    return "상승";
  }
  if (answer === "sideways") {
    return "횡보";
  }
  return "하락";
}
