import Link from "next/link";
import { patterns } from "@/lib/mock-data";

export default function PatternsPage() {
  return (
    <main className="min-h-screen bg-slate-950 px-4 py-8 text-white">
      <div className="mx-auto max-w-5xl">
        <h1 className="text-4xl font-black">패턴별 훈련장</h1>
        <p className="mt-3 text-slate-400">10가지 기본 패턴을 반복해서 훈련합니다.</p>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {patterns.map((pattern) => (
            <Link key={pattern.slug} href="/play" className="rounded-2xl border border-white/10 bg-white/8 p-6 transition hover:border-cyan-300/50">
              <p className="text-2xl font-black">{pattern.name}</p>
              <p className="mt-2 text-slate-400">{pattern.questionCount}문제</p>
              <p className="mt-5 text-sm text-cyan-300">훈련 시작 →</p>
            </Link>
          ))}
        </div>
      </div>
    </main>
  );
}
