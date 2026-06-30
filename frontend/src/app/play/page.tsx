import Link from "next/link";
import { ArrowLeft, Clock3, Heart, Info, Star } from "lucide-react";
import { CandlestickPreview } from "@/components/candlestick-preview";
import { PlayClient } from "@/components/play-client";
import { getTodayQuestion } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function PlayPage() {
  let question;
  try {
    question = await getTodayQuestion();
  } catch {
    question = null;
  }

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto max-w-5xl px-4 py-5">
        <header className="mb-6 flex items-center justify-between">
          <Link href="/" aria-label="홈으로 돌아가기">
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
            <span>문제 7 / 10</span>
            <span>정답률 <strong className="text-fuchsia-300">70%</strong></span>
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
              <span className="font-bold">패턴: {question?.pattern.name ?? "API 연결 필요"}</span>
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
          <section className="rounded-2xl border border-red-400/30 bg-red-950/30 p-6">
            <h2 className="text-2xl font-black text-red-200">문제를 불러올 수 없습니다.</h2>
            <p className="mt-3 text-red-100">
              `pnpm dev:backend` 실행 여부와 `.env`의 `DATABASE_URL` 설정을 확인해주세요.
            </p>
          </section>
        )}
      </div>
    </main>
  );
}
