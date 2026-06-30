import Link from "next/link";
import { BarChart3, BookOpen, ChevronRight, ClipboardList, Flame, Gift, Home, MoreHorizontal, Trophy, UserCircle } from "lucide-react";
import { patterns } from "@/lib/mock-data";

const tabs = [
  { label: "홈", icon: Home, active: true },
  { label: "랭킹", icon: Trophy, active: false },
  { label: "통계", icon: BarChart3, active: false },
  { label: "이벤트", icon: Gift, active: false },
  { label: "더보기", icon: MoreHorizontal, active: false },
];

export default function HomePage() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,#10244c_0%,#020617_42%,#01040b_100%)] px-4 py-6 text-white">
      <div className="mx-auto flex min-h-[calc(100vh-48px)] max-w-5xl flex-col gap-8">
        <header className="flex items-center justify-between">
          <div className="rounded-full border border-white/15 bg-white/8 px-5 py-3 text-lg font-semibold shadow-lg shadow-cyan-500/10">
            <Flame className="mr-2 inline size-5 text-orange-400" />
            연속 퀴즈 <span className="text-yellow-300">7일</span>
          </div>
          <div className="flex overflow-hidden rounded-full border border-white/15 bg-white/8">
            <Link className="flex items-center gap-2 px-5 py-3 font-semibold" href="/rankings">
              <Trophy className="size-5" />
              랭킹
            </Link>
            <Link className="flex items-center gap-2 border-l border-white/10 px-5 py-3 font-semibold" href="/wrong-notes">
              <UserCircle className="size-5" />
              내 정보
            </Link>
          </div>
        </header>

        <section className="text-center">
          <p className="text-2xl font-bold text-slate-200">
            과거는 답을 알고 있다, <span className="text-teal-300">다음 5봉</span>을 맞혀라!
          </p>
          <h1 className="mt-4 text-7xl font-black tracking-tight sm:text-8xl">
            차트<span className="bg-gradient-to-r from-cyan-300 via-blue-500 to-purple-500 bg-clip-text text-transparent">고시</span>
          </h1>
          <p className="mt-5 text-xl text-slate-300">차트 기출문제로 실력을 시험하라</p>
        </section>

        <section className="rounded-[28px] border border-cyan-400/20 bg-slate-950/70 p-5 shadow-2xl shadow-blue-600/20">
          <div className="h-56 rounded-2xl border border-white/10 bg-[linear-gradient(180deg,rgba(56,189,248,.14),rgba(15,23,42,.85)),repeating-linear-gradient(90deg,transparent_0,transparent_58px,rgba(148,163,184,.08)_60px),repeating-linear-gradient(0deg,transparent_0,transparent_38px,rgba(148,163,184,.08)_40px)]">
            <div className="flex h-full items-end justify-between gap-1 px-4 pb-8">
              {Array.from({ length: 34 }).map((_, index) => {
                const up = index % 4 !== 0;
                const height = 36 + ((index * 19) % 92);
                return (
                  <span
                    // Static placeholder candles for the first scaffold screen.
                    key={index}
                    className={up ? "w-3 rounded-sm bg-emerald-400" : "w-3 rounded-sm bg-red-400"}
                    style={{ height }}
                  />
                );
              })}
              <div className="ml-3 flex h-40 w-36 items-center justify-center rounded-xl border border-cyan-300 bg-cyan-400/10 text-5xl font-black text-cyan-300 shadow-lg shadow-cyan-400/20">
                ?
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-4 sm:grid-cols-2">
          <Link
            href="/play"
            className="flex items-center justify-between rounded-[28px] bg-gradient-to-r from-purple-600 to-sky-500 p-7 shadow-xl shadow-blue-500/20 sm:col-span-2"
          >
            <div className="flex items-center gap-5">
              <div className="flex size-20 items-center justify-center rounded-full bg-white/20 text-4xl">◎</div>
              <div>
                <h2 className="text-3xl font-black">오늘의 문제 풀기</h2>
                <p className="mt-1 text-lg text-blue-50">랜덤 1문제 도전!</p>
              </div>
            </div>
            <ChevronRight className="size-9" />
          </Link>
          <Link href="/patterns" className="flex items-center gap-5 rounded-2xl border border-white/10 bg-white/8 p-6">
            <BookOpen className="size-12 text-sky-400" />
            <div>
              <h2 className="text-2xl font-bold">패턴별 훈련장</h2>
              <p className="text-slate-300">10가지 패턴 연습</p>
            </div>
          </Link>
          <Link href="/wrong-notes" className="flex items-center gap-5 rounded-2xl border border-white/10 bg-white/8 p-6">
            <ClipboardList className="size-12 text-slate-400" />
            <div>
              <h2 className="text-2xl font-bold">오답 노트</h2>
              <p className="text-slate-300">내가 틀린 문제 복습</p>
            </div>
          </Link>
        </section>

        <section>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-2xl font-black">10가지 패턴</h2>
            <Link href="/patterns" className="flex items-center gap-1 text-slate-300">
              전체 보기 <ChevronRight className="size-5" />
            </Link>
          </div>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
            {patterns.map((pattern, index) => (
              <Link key={pattern.slug} href="/patterns" className="rounded-2xl border border-white/10 bg-white/8 p-4">
                <div className="mb-3 h-20 rounded-xl bg-gradient-to-br from-cyan-400/15 to-purple-500/15" />
                <p className="font-bold">{index + 1}. {pattern.name}</p>
                <p className="mt-1 text-sm text-slate-400">{pattern.questionCount}문제</p>
              </Link>
            ))}
          </div>
        </section>

        <nav className="sticky bottom-4 mt-auto grid grid-cols-5 rounded-3xl border border-white/10 bg-slate-950/90 p-3 shadow-2xl shadow-black/30 backdrop-blur">
          {tabs.map((tab) => (
            <div key={tab.label} className={tab.active ? "text-center text-sky-400" : "text-center text-slate-500"}>
              <tab.icon className="mx-auto size-6" />
              <p className="mt-1 text-sm font-semibold">{tab.label}</p>
            </div>
          ))}
        </nav>
      </div>
    </main>
  );
}
