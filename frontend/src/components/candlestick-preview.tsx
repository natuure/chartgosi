"use client";

import { useEffect, useRef } from "react";
import { CandlestickSeries, HistogramSeries, LineSeries, createChart } from "lightweight-charts";
import type { CandlestickData, HistogramData, LineData, Time } from "lightweight-charts";
import type { Candle } from "@/lib/types";

export function CandlestickPreview({ candles }: { candles: Candle[] }) {
  const containerRef = useRef<HTMLDivElement>(null);

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
        borderColor: "rgba(148, 163, 184, 0.2)",
      },
      timeScale: {
        borderColor: "rgba(148, 163, 184, 0.2)",
      },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#34d399",
      downColor: "#f87171",
      borderVisible: false,
      wickUpColor: "#34d399",
      wickDownColor: "#f87171",
    });
    candleSeries.setData(candles.map(toCandlestickData));

    const ma20Series = chart.addSeries(LineSeries, {
      color: "#3b82f6",
      lineWidth: 2,
    });
    ma20Series.setData(candles.map((candle) => ({ time: candle.time as Time, value: candle.ma20 } satisfies LineData)));

    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: "#2563eb",
      priceFormat: { type: "volume" },
      priceScaleId: "",
    });
    volumeSeries.setData(
      candles.map((candle) => ({
        time: candle.time as Time,
        value: candle.volume,
        color: candle.close >= candle.open ? "rgba(52, 211, 153, 0.35)" : "rgba(248, 113, 113, 0.35)",
      } satisfies HistogramData)),
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
  }, [candles]);

  return (
    <section className="relative overflow-hidden rounded-2xl border border-white/10 bg-slate-950 p-4">
      <div ref={containerRef} className="h-[420px] w-full" />
      <div className="pointer-events-none absolute bottom-16 right-6 top-14 flex w-32 items-center justify-center rounded-xl border border-dashed border-slate-300/70 bg-slate-900/80 text-5xl font-black text-slate-400">
        ?
      </div>
      <div className="mt-3 flex gap-4 text-sm text-slate-400">
        <span className="text-blue-400">MA20</span>
        <span className="text-purple-400">다음 5봉 가림</span>
      </div>
    </section>
  );
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
