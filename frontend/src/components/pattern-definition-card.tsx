import { CheckCircle2, HelpCircle, Shuffle, XCircle } from "lucide-react";
import type { Pattern } from "@/lib/types";

export function PatternDefinitionCard({
  pattern,
  evidence = [],
  score = null,
  compact = false,
}: {
  pattern: Pattern;
  evidence?: string[];
  score?: number | null;
  compact?: boolean;
}) {
  const definition = pattern.definition;
  const scorecard = definition?.scorecard;

  if (!pattern.description && !definition && evidence.length === 0) {
    return null;
  }

  return (
    <section className="rounded-2xl border border-cyan-300/20 bg-cyan-950/20 p-5">
      <div className="flex items-start gap-3">
        <HelpCircle className="mt-1 size-5 shrink-0 text-cyan-300" />
        <div>
          <p className="text-sm font-bold text-cyan-300">패턴 정의와 판정 근거</p>
          <h2 className="mt-1 text-xl font-black">{pattern.name}</h2>
          <p className="mt-2 leading-7 text-slate-300">{definition?.summary ?? pattern.description}</p>
        </div>
      </div>

      {evidence.length > 0 ? (
        <div className="mt-5">
          <p className="mb-2 text-sm font-bold text-slate-200">이 문제를 이렇게 본 이유</p>
          <ul className="space-y-2">
            {evidence.map((item) => (
              <li key={item} className="flex gap-2 text-sm leading-6 text-slate-300">
                <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-300" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {scorecard ? (
        <div className="mt-5 rounded-xl border border-white/10 bg-slate-950/40 p-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-bold text-slate-200">패턴 스코어보드</p>
              <p className="mt-1 text-sm text-slate-400">
                {scorecard.primaryThreshold}점 이상이면 {pattern.name} 후보로 분류합니다.
              </p>
            </div>
            {score !== null ? (
              <div className="rounded-full bg-cyan-300 px-4 py-2 text-sm font-black text-slate-950">
                현재 {Math.round(score)} / {scorecard.maxScore}점
              </div>
            ) : null}
          </div>
          {!compact ? (
            <>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {scorecard.criteria.map((item) => (
                  <div key={item.key} className="rounded-xl border border-white/10 bg-white/5 p-3">
                    <div className="flex items-start justify-between gap-3">
                      <p className="font-bold text-slate-100">{item.label}</p>
                      <span className="shrink-0 text-sm font-black text-cyan-300">{item.maxPoints}점</span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-slate-400">{item.description}</p>
                  </div>
                ))}
              </div>
              {scorecard.interpretation.length > 0 ? (
                <ul className="mt-4 space-y-1 text-sm text-slate-400">
                  {scorecard.interpretation.map((item) => (
                    <li key={item}>- {item}</li>
                  ))}
                </ul>
              ) : null}
            </>
          ) : null}
        </div>
      ) : null}

      {!compact && definition ? (
        <div className="mt-5 grid gap-4 md:grid-cols-3">
          <DefinitionList title="확인 포인트" icon="check" items={definition.confirmation ?? []} />
          <DefinitionList title="무효 조건" icon="x" items={definition.invalidation ?? []} />
          <DefinitionList title="헷갈리는 패턴" icon="shuffle" items={definition.confusingWith ?? []} />
        </div>
      ) : null}
    </section>
  );
}

function DefinitionList({
  title,
  icon,
  items,
}: {
  title: string;
  icon: "check" | "x" | "shuffle";
  items: string[];
}) {
  if (items.length === 0) {
    return null;
  }

  const Icon = icon === "check" ? CheckCircle2 : icon === "x" ? XCircle : Shuffle;

  return (
    <div>
      <p className="mb-2 flex items-center gap-2 text-sm font-bold text-slate-200">
        <Icon className="size-4 text-cyan-300" />
        {title}
      </p>
      <ul className="space-y-2">
        {items.slice(0, 3).map((item) => (
          <li key={item} className="text-sm leading-6 text-slate-400">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
