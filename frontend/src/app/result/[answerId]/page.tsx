import Link from "next/link";
import { BarChart3, BookOpen, ChevronRight, ClipboardList, RotateCcw, Trophy } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { ExplanationViewTracker } from "@/components/explanation-view-tracker";
import { LoginRequired } from "@/components/login-required";
import { PatternDefinitionCard } from "@/components/pattern-definition-card";
import { getAnswerResult } from "@/lib/api";
import { formatApiError } from "@/lib/api-errors";
import { getServerAccessToken } from "@/lib/server-auth";
import type { AnswerDirection } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function ResultPage({
  params,
}: {
  params: Promise<{ answerId: string }>;
}) {
  const { answerId } = await params;
  const accessToken = await getServerAccessToken();
  let result;
  let apiError: string | null = null;

  if (!accessToken) {
    return (
      <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,#2e1065_0%,#0f172a_38%,#020617_100%)] px-4 py-6 text-white">
        <div className="mx-auto max-w-5xl">
          <LoginRequired nextPath={`/result/${answerId}`} title="결과 확인에는 로그인이 필요합니다" />
        </div>
      </main>
    );
  }

  try {
    result = await getAnswerResult(answerId, accessToken);
  } catch (error) {
    result = null;
    apiError = formatApiError("결과 조회", error);
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,#2e1065_0%,#0f172a_38%,#020617_100%)] px-4 py-6 text-white">
      <div className="mx-auto max-w-5xl">
        <header className="mb-8 rounded-3xl border border-white/10 bg-white/8 p-6">
          <p className="text-sm text-slate-400">답안 ID: {answerId}</p>
          <h1 className="mt-2 text-3xl font-black">문제 풀이 결과</h1>
          <p className="mt-2 text-slate-300">내 계정에 저장된 답안과 실제 다음 5봉을 기준으로 결과를 확인합니다.</p>
        </header>

        {!result ? (
          <section className="rounded-2xl border border-red-400/30 bg-red-950/30 p-6">
            <h2 className="text-2xl font-black text-red-200">결과를 불러오지 못했습니다.</h2>
            <p className="mt-3 text-red-100">{apiError ?? "현재 계정의 답안인지, 백엔드 배포 주소와 answer_id가 올바른지 확인해주세요."}</p>
            <p className="mt-3 text-sm text-red-100">404라면 현재 계정의 답안이 아니거나 없는 답안이고, 401이라면 로그인 세션을 다시 확인해야 합니다.</p>
            <Link href="/play" className="mt-6 inline-flex items-center gap-2 rounded-xl bg-cyan-400 px-5 py-3 font-black text-slate-950">
              문제 다시 풀기
              <ChevronRight className="size-5" />
            </Link>
          </section>
        ) : (
          <>
            <ExplanationViewTracker answerId={result.answerId} enabled={Boolean(result.aiExplanation)} accessToken={accessToken} />
            <section className="mb-8 grid gap-4 lg:grid-cols-[280px_1fr]">
              <div className="rounded-2xl border border-white/10 bg-white/8 p-6 text-center">
                <p className="text-slate-300">정답 여부</p>
                <p className={result.isCorrect ? "mt-4 text-6xl font-black text-emerald-300" : "mt-4 text-6xl font-black text-red-300"}>
                  {result.isCorrect ? "정답" : "오답"}
                </p>
                <p className="mt-4 text-slate-400">패턴: {result.pattern.name}</p>
                <p className="mt-2 text-slate-400">봉 기준: {timeframeLabel(result.timeframe)}</p>
                <p className="mt-2 text-slate-400">내 선택: {answerLabel(result.selectedAnswer)}</p>
                <p className="mt-4 flex items-center justify-center gap-2 font-bold text-orange-300">
                  <Trophy className="size-5" /> 정답: {answerLabel(result.correctAnswer)}
                </p>
              </div>

              <div className="rounded-2xl border border-white/10 bg-white/8 p-6">
                <p className="mb-5 text-slate-300">다른 사용자의 선택 비율</p>
                <div className="space-y-4">
                  {(["up", "sideways", "down"] as const).map((answer) => (
                    <div key={answer}>
                      <div className="mb-2 flex justify-between text-sm text-slate-300">
                        <span>{answerLabel(answer)}</span>
                        <span>{Math.round(result.choiceDistribution[answer] * 100)}%</span>
                      </div>
                      <div className="h-3 rounded-full bg-slate-800">
                        <div
                          className="h-3 rounded-full bg-gradient-to-r from-purple-500 to-cyan-300"
                          style={{ width: `${result.choiceDistribution[answer] * 100}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            <section className="mb-8">
              <h2 className="mb-4 text-2xl font-black">실제 다음 5봉</h2>
              <div className="grid gap-3 sm:grid-cols-5">
                {result.actualNextCandles.map((candle) => (
                  <div key={candle.time} className="rounded-2xl border border-white/10 bg-white/8 p-4">
                    <p className="font-bold">{candle.time}</p>
                    <p className={candle.close >= candle.open ? "mt-3 text-2xl font-black text-red-300" : "mt-3 text-2xl font-black text-blue-300"}>
                      {candle.close}
                    </p>
                    <p className="mt-1 text-sm text-slate-400">O {candle.open} / H {candle.high}</p>
                  </div>
                ))}
              </div>
            </section>

            <section className="mb-8">
              <PatternDefinitionCard pattern={result.pattern} evidence={result.patternEvidence} score={result.patternScore} />
            </section>

            <section className="rounded-2xl border border-white/10 bg-white/8 p-6">
              <h2 className="text-2xl font-black">AI 코멘트</h2>
              <p className="mt-4 leading-8 text-slate-200">{result.aiExplanation ?? "아직 등록된 해설이 없습니다."}</p>
              <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <ResultLink href={`/play?question_id=${encodeURIComponent(result.questionId)}&retry=1`} icon={RotateCcw} label="같은 문제 다시 풀기" />
                <ResultLink href={`/play?pattern=${encodeURIComponent(result.pattern.slug)}`} icon={BookOpen} label="같은 패턴 훈련" />
                <ResultLink href="/wrong-notes" icon={ClipboardList} label="오답노트 보기" />
                <ResultLink href="/stats" icon={BarChart3} label="통계 보기" />
              </div>
            </section>
          </>
        )}
      </div>
    </main>
  );
}

function ResultLink({
  href,
  icon: Icon,
  label,
}: {
  href: string;
  icon: LucideIcon;
  label: string;
}) {
  return (
    <Link href={href} className="flex items-center justify-center gap-2 rounded-2xl border border-white/10 px-4 py-4 font-bold transition hover:border-cyan-300/50">
      <Icon className="size-5" />
      {label}
    </Link>
  );
}

function answerLabel(answer: AnswerDirection) {
  return {
    up: "상승",
    sideways: "횡보",
    down: "하락",
  }[answer];
}

function timeframeLabel(timeframe: string) {
  return {
    "1d": "일봉",
    "1w": "주봉",
  }[timeframe] ?? timeframe;
}
