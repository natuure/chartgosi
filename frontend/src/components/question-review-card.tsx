"use client";

import { useCallback, useMemo, useState } from "react";
import Link from "next/link";
import { CheckCircle2, ExternalLink, Save, XCircle } from "lucide-react";
import { CandlestickPreview } from "@/components/candlestick-preview";
import { updateQuestionReview } from "@/lib/api";
import { formatApiError } from "@/lib/api-errors";
import { getBrowserAccessToken } from "@/lib/browser-auth";
import type { Candle, PatternMarker, ReviewQuestion, ReviewStatus } from "@/lib/types";

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
  const initialMarkers = useMemo(
    () => normalizePatternMarkers(question.patternMarkers, question.pattern.slug),
    [question.pattern.slug, question.patternMarkers],
  );
  const [reviewStatus, setReviewStatus] = useState<ReviewStatus>(question.reviewStatus);
  const [reviewNote, setReviewNote] = useState(question.reviewNote);
  const [markersText, setMarkersText] = useState(() => JSON.stringify(initialMarkers, null, 2));
  const [savedQuestion, setSavedQuestion] = useState(question);
  const [selectedCandle, setSelectedCandle] = useState<{ candle: Candle; index: number } | null>(null);
  const [markerDraftLabel, setMarkerDraftLabel] = useState(() => defaultMarkerLabel(question.pattern.slug));
  const [markerDraftPosition, setMarkerDraftPosition] = useState<PatternMarker["position"]>("aboveBar");
  const [markerDraftColor, setMarkerDraftColor] = useState("#facc15");
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const allReviewCandles = useMemo(
    () => [...savedQuestion.chartData, ...savedQuestion.actualNextCandles],
    [savedQuestion.actualNextCandles, savedQuestion.chartData],
  );
  const markerPresets = useMemo(() => getMarkerPresets(savedQuestion.pattern.slug), [savedQuestion.pattern.slug]);

  const parsedMarkers = useMemo(() => {
    try {
      const value = JSON.parse(markersText) as PatternMarker[];
      return Array.isArray(value) ? normalizePatternMarkers(value, savedQuestion.pattern.slug) : [];
    } catch {
      return normalizePatternMarkers(savedQuestion.patternMarkers, savedQuestion.pattern.slug);
    }
  }, [markersText, savedQuestion.pattern.slug, savedQuestion.patternMarkers]);
  const markerRows = useMemo(
    () => parsedMarkers.map((marker) => ({ marker, candle: findCandleByTime(allReviewCandles, marker.time) })),
    [allReviewCandles, parsedMarkers],
  );
  const scoreRows = useMemo(() => toScoreRows(savedQuestion), [savedQuestion]);
  const handleCandleClick = useCallback((candle: Candle, index: number) => {
    setSelectedCandle({ candle, index });
  }, []);

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
      const normalizedMarkers = normalizePatternMarkers(updated.patternMarkers, updated.pattern.slug);
      setSavedQuestion(updated);
      setReviewStatus(updated.reviewStatus);
      setReviewNote(updated.reviewNote);
      setMarkersText(JSON.stringify(normalizedMarkers, null, 2));
      setMessage("검수 내용이 저장되었습니다.");
    } catch (error) {
      setError(formatApiError("검수 저장", error));
    } finally {
      setIsSaving(false);
    }
  }

  function addMarkerFromCandle(index: number, label: string, position: PatternMarker["position"], color: string) {
    const candle = allReviewCandles[index];
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

  function upsertSelectedMarker() {
    if (!selectedCandle) {
      setError("먼저 차트에서 봉을 클릭하세요.");
      return;
    }

    const label = markerDraftLabel.trim();
    if (!label) {
      setError("마커 라벨을 입력하세요.");
      return;
    }

    const nextMarkers = sortMarkersByChartOrder(
      [
        ...parsedMarkers.filter((marker) => marker.label !== label),
        {
          time: selectedCandle.candle.time,
          label,
          position: markerDraftPosition,
          shape: "circle" as const,
          color: markerDraftColor,
        },
      ],
      allReviewCandles,
    );
    setMarkersText(JSON.stringify(nextMarkers, null, 2));
    setError(null);
    setMessage(`${label} 마커를 ${selectedCandle.index + 1}번째 봉으로 맞췄습니다. 저장 버튼을 누르면 DB에 반영됩니다.`);
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
        onCandleClick={handleCandleClick}
      />

      <section className="mt-5 grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
            <h3 className="font-black text-cyan-100">이 문제를 이렇게 본 이유</h3>
            <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-300">
              {savedQuestion.patternEvidence.length > 0 ? (
                savedQuestion.patternEvidence.map((item) => <li key={item}>• {item}</li>)
              ) : (
                <li className="text-slate-500">저장된 근거 문구가 없습니다.</li>
              )}
            </ul>
          </div>

          <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h3 className="font-black text-cyan-100">검수 핵심 지점</h3>
                <p className="mt-1 text-xs text-slate-400">봉 번호는 화면에 보이는 차트의 왼쪽부터 1번째로 계산합니다.</p>
              </div>
              <span className="text-xs font-bold text-slate-400">{markerRows.length}개 마커</span>
            </div>
            {markerRows.length > 0 ? (
              <div className="mt-3 overflow-x-auto">
                <table className="w-full min-w-[620px] text-left text-xs">
                  <thead className="text-slate-400">
                    <tr className="border-b border-white/10">
                      <th className="py-2 pr-3">라벨</th>
                      <th className="py-2 pr-3">봉</th>
                      <th className="py-2 pr-3">날짜</th>
                      <th className="py-2 pr-3">시가</th>
                      <th className="py-2 pr-3">고가</th>
                      <th className="py-2 pr-3">저가</th>
                      <th className="py-2">종가</th>
                    </tr>
                  </thead>
                  <tbody>
                    {markerRows.map(({ marker, candle }) => (
                      <tr key={`${marker.time}-${marker.label}`} className="border-b border-white/5 text-slate-200 last:border-0">
                        <td className="py-2 pr-3 font-bold" style={{ color: marker.color }}>
                          {marker.label}
                        </td>
                        <td className="py-2 pr-3">{candle ? `${candle.index + 1}번째` : "-"}</td>
                        <td className="py-2 pr-3">{marker.time}</td>
                        <td className="py-2 pr-3">{candle ? formatNumber(candle.open) : "-"}</td>
                        <td className="py-2 pr-3">{candle ? formatNumber(candle.high) : "-"}</td>
                        <td className="py-2 pr-3">{candle ? formatNumber(candle.low) : "-"}</td>
                        <td className="py-2">{candle ? formatNumber(candle.close) : "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="mt-3 rounded-xl border border-dashed border-white/10 p-4 text-sm text-slate-400">
                아직 저장된 핵심 지점 마커가 없습니다. 오른쪽 마커 JSON 또는 빠른 마커 버튼으로 추가하세요.
              </p>
            )}
          </div>

          <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h3 className="font-black text-cyan-100">스코어 항목</h3>
                <p className="mt-1 text-xs text-slate-400">공식 패턴 정의의 scorecard key와 문제별 계산값을 맞춰 봅니다.</p>
              </div>
              <span className="text-xs font-bold text-slate-400">
                총점 {savedQuestion.patternScore ?? "-"} / {savedQuestion.pattern.definition?.scorecard?.maxScore ?? 100}
              </span>
            </div>
            {scoreRows.length > 0 ? (
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                {scoreRows.map((row) => (
                  <div key={row.key} className="rounded-xl border border-white/10 bg-white/5 p-3">
                    <div className="flex items-start justify-between gap-3">
                      <p className="font-bold text-slate-100">{row.label}</p>
                      <span className="shrink-0 text-sm font-black text-cyan-300">{row.value}</span>
                    </div>
                    {row.description ? <p className="mt-2 text-xs leading-5 text-slate-400">{row.description}</p> : null}
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-3 rounded-xl border border-dashed border-white/10 p-4 text-sm text-slate-400">
                저장된 스코어 breakdown이 없습니다. 다음 문제 생성 때 항목별 점수 저장 여부를 확인하세요.
              </p>
            )}
          </div>
        </div>

        <div className="space-y-3">
          <div className="rounded-2xl border border-cyan-300/20 bg-cyan-950/20 p-3">
            <p className="text-sm font-black text-cyan-100">차트 클릭으로 마커 추가</p>
            {selectedCandle ? (
              <div className="mt-3 rounded-xl border border-white/10 bg-slate-950/60 p-3 text-xs leading-5 text-slate-300">
                <p className="font-bold text-white">
                  선택 봉: {selectedCandle.index + 1}번째 · {selectedCandle.candle.time}
                </p>
                <p>
                  O {formatNumber(selectedCandle.candle.open)} · H {formatNumber(selectedCandle.candle.high)} · L {formatNumber(selectedCandle.candle.low)} · C {formatNumber(selectedCandle.candle.close)}
                </p>
              </div>
            ) : (
              <p className="mt-2 text-xs leading-5 text-slate-400">차트에서 핵심 봉을 클릭한 뒤 라벨을 선택하세요.</p>
            )}

            <div className="mt-3 flex flex-wrap gap-2">
              {markerPresets.map((preset) => (
                <button
                  key={preset.label}
                  type="button"
                  className={`rounded-lg border px-3 py-1 text-xs font-bold ${markerDraftLabel === preset.label ? "border-cyan-200 bg-cyan-300 text-slate-950" : "border-white/10 bg-slate-900 text-slate-200"}`}
                  onClick={() => {
                    setMarkerDraftLabel(preset.label);
                    setMarkerDraftPosition(preset.position);
                    setMarkerDraftColor(preset.color);
                  }}
                >
                  {preset.label}
                </button>
              ))}
            </div>

            <div className="mt-3 grid gap-2 sm:grid-cols-[1fr_120px]">
              <input
                className="rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-300"
                value={markerDraftLabel}
                onChange={(event) => setMarkerDraftLabel(event.target.value)}
                placeholder="마커 라벨"
              />
              <select
                className="rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-300"
                value={markerDraftPosition}
                onChange={(event) => setMarkerDraftPosition(event.target.value as PatternMarker["position"])}
              >
                <option value="aboveBar">위</option>
                <option value="belowBar">아래</option>
                <option value="inBar">봉 안</option>
              </select>
            </div>

            <button
              type="button"
              className="mt-3 w-full rounded-xl bg-cyan-300 px-4 py-2 text-sm font-black text-slate-950 disabled:opacity-50"
              disabled={!selectedCandle}
              onClick={upsertSelectedMarker}
            >
              선택 봉에 마커 추가/보정
            </button>
            <p className="mt-2 text-xs leading-5 text-slate-400">
              같은 라벨이 이미 있으면 선택한 봉으로 자동 교체됩니다. 최종 반영은 아래 검수 저장 버튼으로 합니다.
            </p>
          </div>

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

function findCandleByTime(candles: ReviewQuestion["chartData"], time: string) {
  const index = candles.findIndex((candle) => candle.time === time);
  const candle = candles[index];
  return candle ? { ...candle, index } : null;
}

function toScoreRows(question: ReviewQuestion) {
  const breakdown = question.patternScoreBreakdown;
  if (!breakdown) {
    return [];
  }

  const criteria = question.pattern.definition?.scorecard?.criteria ?? [];
  const criteriaByKey = new Map(criteria.map((item) => [item.key, item]));

  return Object.entries(breakdown).map(([key, value]) => {
    const criterion = criteriaByKey.get(key);
    return {
      key,
      label: criterion?.label ?? key,
      description: criterion?.description ?? "",
      value: typeof value === "number" ? `${formatNumber(value)}점` : String(value),
    };
  });
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits: Math.abs(value) >= 1000 ? 0 : 2,
  }).format(value);
}

function sortMarkersByChartOrder(markers: PatternMarker[], candles: Candle[]) {
  const indexByTime = new Map(candles.map((candle, index) => [candle.time, index]));
  return [...markers].sort((left, right) => {
    const leftIndex = indexByTime.get(left.time) ?? Number.MAX_SAFE_INTEGER;
    const rightIndex = indexByTime.get(right.time) ?? Number.MAX_SAFE_INTEGER;
    if (leftIndex !== rightIndex) {
      return leftIndex - rightIndex;
    }
    return left.label.localeCompare(right.label, "ko");
  });
}

function normalizePatternMarkers(markers: PatternMarker[], patternSlug: string) {
  return markers.map((marker, index) => ({
    ...marker,
    label: normalizeMarkerLabel(marker, index, markers, patternSlug),
  }));
}

function normalizeMarkerLabel(marker: PatternMarker, index: number, markers: PatternMarker[], patternSlug: string) {
  if (!isCorruptMarkerLabel(marker.label)) {
    return marker.label;
  }

  if (patternSlug === "new-high-breakout") {
    return index === markers.length - 1 || marker.shape === "arrowUp" ? "돌파봉" : "이전 신고가";
  }

  if (patternSlug === "triangle") {
    if (index === markers.length - 1 || marker.shape === "arrowUp") {
      return "피벗 돌파";
    }
    const suffix = marker.label.match(/\d+/)?.[0] ?? `${index + 1}`;
    return `국소 고점${suffix}`;
  }

  if (patternSlug === "box-breakout") {
    if (index === markers.length - 1 || marker.shape === "arrowUp") {
      return "돌파봉";
    }
    const suffix = marker.label.match(/\d+/)?.[0] ?? `${index + 1}`;
    return marker.position === "belowBar" ? `하단 지지${suffix}` : `상단 저항${suffix}`;
  }

  return getMarkerPresets(patternSlug)[index]?.label ?? "핵심 봉";
}

function isCorruptMarkerLabel(label: string) {
  return /^[?\s\d]+$/.test(label.trim());
}

function defaultMarkerLabel(patternSlug: string) {
  return getMarkerPresets(patternSlug)[0]?.label ?? "핵심 봉";
}

function getMarkerPresets(patternSlug: string): PatternMarker[] {
  const common = {
    position: "aboveBar" as const,
    shape: "circle" as const,
  };

  const presets: Record<string, PatternMarker[]> = {
    "cup-and-handle": [
      { ...common, time: "", label: "급등 시작", position: "belowBar", color: "#22c55e" },
      { ...common, time: "", label: "왼쪽림", color: "#f97316" },
      { ...common, time: "", label: "컵 바닥", position: "belowBar", color: "#38bdf8" },
      { ...common, time: "", label: "오른쪽림", color: "#facc15" },
      { ...common, time: "", label: "핸들 끝", color: "#c084fc" },
    ],
    "double-bottom": [
      { ...common, time: "", label: "1차 저점", position: "belowBar", color: "#38bdf8" },
      { ...common, time: "", label: "넥라인", color: "#facc15" },
      { ...common, time: "", label: "2차 저점", position: "belowBar", color: "#22c55e" },
      { ...common, time: "", label: "회복봉", color: "#c084fc" },
    ],
    "box-breakout": [
      { ...common, time: "", label: "상단 저항", color: "#facc15" },
      { ...common, time: "", label: "하단 지지", position: "belowBar", color: "#38bdf8" },
      { ...common, time: "", label: "돌파봉", color: "#22c55e" },
    ],
    "new-high-breakout": [
      { ...common, time: "", label: "이전 신고가", color: "#facc15" },
      { ...common, time: "", label: "돌파봉", color: "#22c55e" },
    ],
    pullback: [
      { ...common, time: "", label: "선행 고점", color: "#facc15" },
      { ...common, time: "", label: "조정 시작", color: "#c084fc" },
      { ...common, time: "", label: "확정봉", position: "belowBar", color: "#22c55e" },
    ],
    triangle: [
      { ...common, time: "", label: "국소 고점", color: "#facc15" },
      { ...common, time: "", label: "수축 저점", position: "belowBar", color: "#38bdf8" },
      { ...common, time: "", label: "피벗 돌파", color: "#22c55e" },
    ],
    flag: [
      { ...common, time: "", label: "급등 시작", position: "belowBar", color: "#22c55e" },
      { ...common, time: "", label: "급등 고점", color: "#facc15" },
      { ...common, time: "", label: "조정 확인", position: "belowBar", color: "#38bdf8" },
    ],
    "flat-base": [
      { ...common, time: "", label: "선행 고점", color: "#facc15" },
      { ...common, time: "", label: "베이스 시작", position: "belowBar", color: "#38bdf8" },
      { ...common, time: "", label: "Tight 3주", color: "#c084fc" },
      { ...common, time: "", label: "MA10 근접", position: "belowBar", color: "#22c55e" },
    ],
    "bullish-engulfing": [
      { ...common, time: "", label: "음봉", position: "belowBar", color: "#3b82f6" },
      { ...common, time: "", label: "양봉 장악", color: "#ef4444" },
      { ...common, time: "", label: "다음 봉", color: "#facc15" },
    ],
    "early-stage2": [
      { ...common, time: "", label: "베이스 시작", position: "belowBar", color: "#38bdf8" },
      { ...common, time: "", label: "상단", color: "#facc15" },
      { ...common, time: "", label: "돌파봉", color: "#22c55e" },
    ],
  };

  return (
    presets[patternSlug] ?? [
      { ...common, time: "", label: "핵심 봉", color: "#facc15" },
      { ...common, time: "", label: "확정봉", color: "#22c55e" },
    ]
  );
}
