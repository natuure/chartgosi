import Link from "next/link";
import { ChevronRight, RotateCcw, Trophy } from "lucide-react";
import { patterns } from "@/lib/mock-data";

export default async function ResultPage({
  params,
}: {
  params: Promise<{ answerId: string }>;
}) {
  const { answerId } = await params;

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,#2e1065_0%,#0f172a_38%,#020617_100%)] px-4 py-6 text-white">
      <div className="mx-auto max-w-5xl">
        <header className="mb-8 rounded-3xl border border-white/10 bg-white/8 p-6">
          <p className="text-sm text-slate-400">답안 ID: {answerId}</p>
          <h1 className="mt-2 text-3xl font-black">AI 분석 리포트 ✦</h1>
          <p className="mt-2 text-slate-300">최근 풀이 데이터를 바탕으로 차트 판단 습관을 요약합니다.</p>
        </header>

        <section className="mb-8 grid gap-4 lg:grid-cols-[260px_1fr]">
          <div className="rounded-2xl border border-white/10 bg-white/8 p-6 text-center">
            <p className="text-slate-300">종합 점수</p>
            <p className="mt-4 text-6xl font-black text-purple-300">842</p>
            <p className="mt-2 text-slate-400">/ 1200</p>
            <p className="mt-4 flex items-center justify-center gap-2 font-bold text-orange-300">
              <Trophy className="size-5" /> 상위 18%
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/8 p-6">
            <p className="mb-5 text-slate-300">점수 추이</p>
            <div className="flex h-52 items-end gap-3 border-b border-l border-white/10 p-4">
              {[320, 540, 610, 620, 810, 842].map((score) => (
                <div key={score} className="flex flex-1 flex-col items-center gap-2">
                  <div className="w-full rounded-t-xl bg-gradient-to-t from-purple-700 to-cyan-300" style={{ height: score / 7 }} />
                  <span className="text-xs text-slate-400">{score}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mb-8">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-2xl font-black">패턴별 정답률</h2>
            <Link href="/patterns" className="flex items-center gap-1 text-slate-300">
              자세히 보기 <ChevronRight className="size-5" />
            </Link>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            {patterns.map((pattern, index) => (
              <div key={pattern.slug} className="rounded-2xl border border-white/10 bg-white/8 p-4">
                <p className="font-bold">{pattern.name}</p>
                <div className="my-3 h-12 rounded-lg bg-gradient-to-br from-cyan-400/15 to-purple-500/15" />
                <p className="text-3xl font-black">{[89, 78, 65, 72, 91, 58, 62, 73, 80, 45][index]}%</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-white/10 bg-white/8 p-6">
          <h2 className="text-2xl font-black">AI 코멘트</h2>
          <p className="mt-4 leading-8 text-slate-200">
            전반적으로 추세 추종 능력이 뛰어납니다. 특히 눌림목 매매와 컵앤핸들을 잘 파악하고 있어요.
            거래량 관련 문제의 정답률이 낮은 편이므로 거래량을 활용한 매집/분산 패턴을 더 연습해보세요.
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
      </div>
    </main>
  );
}
