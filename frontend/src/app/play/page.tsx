import Link from "next/link";
import { ArrowLeft, Clock3, Heart, Info, Star } from "lucide-react";
import { CandlestickPreview } from "@/components/candlestick-preview";
import { PlayClient } from "@/components/play-client";
import { getTodayQuestion } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function PlayPage({
  searchParams,
}: {
  searchParams: Promise<{ pattern?: string }>;
}) {
  const { pattern } = await searchParams;
  let question;

  try {
    question = await getTodayQuestion(pattern);
  } catch {
    question = null;
  }

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto max-w-5xl px-4 py-5">
        <header className="mb-6 flex items-center justify-between">
          <Link href={pattern ? "/patterns" : "/"} aria-label="뒤로 가기">
            <ArrowLeft className="size-8 text-slate-300" />
          </Link>
          <h1 className="text-2xl font-black">차트고시 🎓</h1>
          <div className="flex items-center gap-3 rounded-full border border-white/10 bg-white/8 px-4 py-2 font-bold">
            <Heart className="size-5 fill-red-500 text-red-500" /> 4/5
            <span className="h-5 w-px bg-white/15" />
            <Clock3 className="size-5 text-slate-300" /> 29:32
          </div>
        </header>

        <section className="mb-6">
          <div className="mb-3 flex items-center justify-between text-slate-300">
            <span>{pattern ? "패턴별 훈련" : "오늘의 문제"}</span>
            <span>
              정답률 <strong className="text-fuchsia-300">{question ? Math.round(question.publicAccuracy * 100) : 0}%</strong>
            </span>
          </div>
          <div className="h-3 rounded-full bg-slate-800">
            <div className="h-3 w-[70%] rounded-full bg-gradient-to-r from-purple-500 to-fuchsia-400" />
          </div>
        </section>

        <section className="mb-6 flex items-center justify-between">
          <div>
            <div className="mb-4 flex items-center gap-3">
              <span className="rounded-full border border-fuchsia-400/70 bg-fuchsia-500/20 px-4 py-1 font-bold text-fuchsia-200">
                {question?.difficultyLabel ?? "대기"}
              </span>
              <span className="font-bold">패턴: {question?.pattern.name ?? "문제 없음"}</span>
              <Info className="size-5 text-slate-400" />
            </div>
            <h2 className="text-3xl font-black">
              다음 <span className="text-orange-300">5봉</span>은 어떻게 될까?
            </h2>
            <p className="mt-3 text-slate-400">과거 차트를 보고 다음 5개의 캔들을 맞혀보세요.</p>
          </div>
          <button className="flex items-center gap-2 text-slate-300" type="button">
            <Star className="size-6" />
            즐겨찾기
          </button>
        </section>

        {question ? (
          <>
            <CandlestickPreview candles={question.chartData} />
            <PlayClient question={question} />
          </>
        ) : (
          <section className="rounded-2xl border border-yellow-400/30 bg-yellow-950/30 p-6">
            <h2 className="text-2xl font-black text-yellow-100">이 패턴에는 아직 풀 수 있는 문제가 없습니다.</h2>
            <p className="mt-3 text-yellow-50">
              현재 seed 데이터에는 컵앤핸들 문제 1개만 들어 있습니다. 다른 패턴 문제는 이후 seed 확장 단계에서 추가하면 됩니다.
            </p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row">
              <Link href="/patterns" className="rounded-xl border border-white/10 px-5 py-3 text-center font-bold">
                패턴별 훈련장으로
              </Link>
              <Link href="/play" className="rounded-xl bg-cyan-400 px-5 py-3 text-center font-black text-slate-950">
                오늘의 문제 풀기
              </Link>
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
