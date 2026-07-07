"use client";

import { useEffect, useMemo, useRef } from "react";
import {
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  PriceScaleMode,
  createChart,
} from "lightweight-charts";
import type { CandlestickData, HistogramData, LineData, Time } from "lightweight-charts";
import type { Candle } from "@/lib/types";

const MOVING_AVERAGE_COLORS = ["#38bdf8", "#22c55e", "#f59e0b", "#a855f7"];

type CandlestickPreviewProps = {
  candles: Candle[];
  timeframe: string;
  patternSlug?: string;
  revealedCandles?: Candle[];
  showHiddenOverlay?: boolean;
};

type MovingAverageConfig = {
  periods: number[];
  unit: string;
};

export function CandlestickPreview({
  candles,
  timeframe,
  patternSlug,
  revealedCandles = [],
  showHiddenOverlay = true,
}: CandlestickPreviewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartCandles = useMemo(() => [...candles, ...revealedCandles], [candles, revealedCandles]);
  const movingAverage = useMemo(() => getMovingAverageConfig(timeframe, patternSlug), [timeframe, patternSlug]);

  useEffect(() => {
    if (!containerRef.current) {
      return;
    }

    const chart = createChart(containerRef.current, {
      height: 420,
      layout: {
        background: { color: "#020617" },
        textColor: "#94a3b8",
      },
      grid: {
        vertLines: { color: "rgba(148, 163, 184, 0.12)" },
        horzLines: { color: "rgba(148, 163, 184, 0.12)" },
      },
      rightPriceScale: {
        mode: PriceScaleMode.Logarithmic,
        borderColor: "rgba(148, 163, 184, 0.2)",
      },
      timeScale: {
        borderColor: "rgba(148, 163, 184, 0.2)",
      },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#ef4444",
      downColor: "#3b82f6",
      borderVisible: false,
      wickUpColor: "#ef4444",
      wickDownColor: "#3b82f6",
    });
    candleSeries.setData(chartCandles.map(toCandlestickData));

    movingAverage.periods.forEach((period, index) => {
      const maSeries = chart.addSeries(LineSeries, {
        color: MOVING_AVERAGE_COLORS[index] ?? "#94a3b8",
        lineWidth: 2,
        lastValueVisible: false,
        priceLineVisible: false,
      });
      maSeries.setData(toMovingAverageData(chartCandles, period));
    });

    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: "#2563eb",
      priceFormat: { type: "volume" },
      priceScaleId: "",
    });
    volumeSeries.setData(
      chartCandles.map(
        (candle) =>
          ({
            time: candle.time as Time,
            value: candle.volume,
            color: candle.close >= candle.open ? "rgba(239, 68, 68, 0.38)" : "rgba(59, 130, 246, 0.38)",
          }) satisfies HistogramData,
      ),
    );
    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.82,
        bottom: 0,
      },
    });

    chart.timeScale().fitContent();

    const resize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    resize();
    window.addEventListener("resize", resize);

    return () => {
      window.removeEventListener("resize", resize);
      chart.remove();
    };
  }, [chartCandles, movingAverage]);

  return (
    <section className="relative overflow-hidden rounded-2xl border border-white/10 bg-slate-950 p-4">
      <div ref={containerRef} className="h-[420px] w-full" />
      {showHiddenOverlay ? (
        <div className="pointer-events-none absolute bottom-16 right-6 top-14 flex w-32 items-center justify-center rounded-xl border border-dashed border-slate-300/70 bg-slate-900/80 text-5xl font-black text-slate-400">
          ?
        </div>
      ) : null}
      <div className="mt-3 flex flex-wrap gap-4 text-sm text-slate-400">
        <span className="text-slate-300">로그 스케일</span>
        {movingAverage.periods.map((period, index) => (
          <span key={period} style={{ color: MOVING_AVERAGE_COLORS[index] }}>
            MA{period}
            {movingAverage.unit}
          </span>
        ))}
        <span className="text-red-400">양봉</span>
        <span className="text-blue-400">음봉</span>
        {showHiddenOverlay ? (
          <span className="text-purple-400">다음 5봉 가림</span>
        ) : (
          <span className="text-purple-400">다음 {revealedCandles.length}봉 표시</span>
        )}
      </div>
    </section>
  );
}

function getMovingAverageConfig(timeframe: string, patternSlug?: string): MovingAverageConfig {
  if (timeframe === "1w") {
    return { periods: [10, 30, 40], unit: "주" };
  }

  if (patternSlug === "pullback") {
    return { periods: [5, 10, 20, 60], unit: "일" };
  }

  return { periods: [50, 150, 200], unit: "일" };
}

function toCandlestickData(candle: Candle): CandlestickData {
  return {
    time: candle.time as Time,
    open: candle.open,
    high: candle.high,
    low: candle.low,
    close: candle.close,
  };
}

function toMovingAverageData(candles: Candle[], period: number): LineData[] {
  return candles.map((candle, index) => {
    const precomputedValue = getPrecomputedMovingAverage(candle, period);
    if (typeof precomputedValue === "number" && Number.isFinite(precomputedValue)) {
      return { time: candle.time as Time, value: precomputedValue };
    }

    const start = Math.max(0, index - period + 1);
    const averageCandles = candles.slice(start, index + 1);
    const average = averageCandles.reduce((sum, item) => sum + item.close, 0) / averageCandles.length;
    return { time: candle.time as Time, value: Number(average.toFixed(2)) };
  });
}

function getPrecomputedMovingAverage(candle: Candle, period: number): number | undefined {
  const key = `ma${period}` as keyof Candle;
  const value = candle[key];
  return typeof value === "number" ? value : undefined;
}
