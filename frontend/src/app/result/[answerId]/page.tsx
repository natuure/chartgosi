import Link from "next/link";
import { ChevronRight, RotateCcw, Trophy } from "lucide-react";
import { getAnswerResult } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ResultPage({
  params,
}: {
  params: Promise<{ answerId: string }>;
}) {
  const { answerId } = await params;
  let result;
  try {
    result = await getAnswerResult(answerId);
  } catch {
    result = null;
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,#2e1065_0%,#0f172a_38%,#020617_100%)] px-4 py-6 text-white">
      <div className="mx-auto max-w-5xl">
        <header className="mb-8 rounded-3xl border border-white/10 bg-white/8 p-6">
          <p className="text-sm text-slate-400">답안 ID: {answerId}</p>
          <h1 className="mt-2 text-3xl font-black">문제 풀이 결과 ✦</h1>
          <p className="mt-2 text-slate-300">DB에 저장된 답안과 실제 다음 5봉 기준으로 결과를 확인합니다.</p>
        </header>

        {!result ? (
          <section className="rounded-2xl border border-red-400/30 bg-red-950/30 p-6">
            <h2 className="text-2xl font-black text-red-200">결과를 불러올 수 없습니다.</h2>
            <p className="mt-3 text-red-100">백엔드 서버, DATABASE_URL, answer_id를 확인해주세요.</p>
          </section>
        ) : (
          <>

        <section className="mb-8 grid gap-4 lg:grid-cols-[260px_1fr]">
          <div className="rounded-2xl border border-white/10 bg-white/8 p-6 text-center">
            <p className="text-slate-300">정답 여부</p>
            <p className={result.isCorrect ? "mt-4 text-6xl font-black text-emerald-300" : "mt-4 text-6xl font-black text-red-300"}>
              {result.isCorrect ? "정답" : "오답"}
            </p>
            <p className="mt-2 text-slate-400">내 선택: {answerLabel(result.selectedAnswer)}</p>
            <p className="mt-4 flex items-center justify-center gap-2 font-bold text-orange-300">
              <Trophy className="size-5" /> 정답: {answerLabel(result.correctAnswer)}
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/8 p-6">
            <p className="mb-5 text-slate-300">다른 사용자 선택 비율</p>
            <div className="space-y-4">
              {(["up", "sideways", "down"] as const).map((answer) => (
                <div key={answer}>
                  <div className="mb-2 flex justify-between text-sm text-slate-300">
                    <span>{answerLabel(answer)}</span>
                    <span>{Math.round(result.choiceDistribution[answer] * 100)}%</span>
                  </div>
                  <div className="h-3 rounded-full bg-slate-800">
                    <div className="h-3 rounded-full bg-gradient-to-r from-purple-500 to-cyan-300" style={{ width: `${result.choiceDistribution[answer] * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mb-8">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-2xl font-black">실제 다음 5봉</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-5">
            {result.actualNextCandles.map((candle) => (
              <div key={candle.time} className="rounded-2xl border border-white/10 bg-white/8 p-4">
                <p className="font-bold">{candle.time}</p>
                <p className={candle.close >= candle.open ? "mt-3 text-2xl font-black text-emerald-300" : "mt-3 text-2xl font-black text-red-300"}>
                  {candle.close}
                </p>
                <p className="mt-1 text-sm text-slate-400">O {candle.open} / H {candle.high}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-white/10 bg-white/8 p-6">
          <h2 className="text-2xl font-black">AI 코멘트</h2>
          <p className="mt-4 leading-8 text-slate-200">
            {result.aiExplanation ?? "아직 등록된 해설이 없습니다."}
          </p>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <Link href="/play" className="flex flex-1 items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-purple-600 to-blue-500 py-4 font-black">
              맞춤 훈련 시작하기 <ChevronRight className="size-5" />
            </Link>
            <Link href="/play" className="flex items-center justify-center gap-2 rounded-2xl border border-white/10 px-6 py-4 font-bold">
              <RotateCcw className="size-5" /> 다른 문제 풀기
            </Link>
          </div>
        </section>
          </>
        )}
      </div>
    </main>
  );
}

function answerLabel(answer: "up" | "sideways" | "down") {
  return {
    up: "상승",
    sideways: "횡보",
    down: "하락",
  }[answer];
}
