import Link from "next/link";
import { ArrowLeft, Clock3, Heart, Info, Star } from "lucide-react";
import { CandlestickPreview } from "@/components/candlestick-preview";
import { sampleQuestion } from "@/lib/mock-data";

const answers = [
  { value: "up", label: "상승할 것 같다", hint: "확률 70% 이상", accent: "text-emerald-300" },
  { value: "sideways", label: "횡보할 것 같다", hint: "±3% 이내", accent: "text-yellow-300" },
  { value: "down", label: "하락할 것 같다", hint: "확률 70% 이상", accent: "text-red-300" },
  { value: "volatile", label: "급등/급락할 것 같다", hint: "확률 50% 이상", accent: "text-purple-300" },
];

export default function PlayPage() {
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
                {sampleQuestion.difficultyLabel}
              </span>
              <span className="font-bold">패턴: {sampleQuestion.pattern.name}</span>
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

        <CandlestickPreview candles={sampleQuestion.chartData} />

        <section className="mt-6">
          <p className="mb-3 text-slate-300">하나를 선택하세요</p>
          <div className="grid gap-4 sm:grid-cols-2">
            {answers.map((answer) => (
              <button key={answer.value} className="rounded-2xl border border-white/10 bg-white/8 p-6 text-left transition hover:border-cyan-300/60" type="button">
                <p className={`text-xl font-black ${answer.accent}`}>{answer.label}</p>
                <p className="mt-1 text-slate-400">{answer.hint}</p>
              </button>
            ))}
          </div>
          <Link
            href="/result/mock-answer"
            className="mt-6 block rounded-2xl bg-slate-800 py-5 text-center text-xl font-black text-slate-300 transition hover:bg-slate-700"
          >
            정답 제출하기
          </Link>
        </section>
      </div>
    </main>
  );
}
