import Link from "next/link";
import { ArrowLeft, BookOpen, ChevronRight } from "lucide-react";
import { getPatterns } from "@/lib/api";
import type { Pattern } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function PatternsPage() {
  let patterns: Pattern[] = [];
  let hasApiError = false;

  try {
    patterns = await getPatterns();
  } catch {
    hasApiError = true;
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,#164e63_0%,#0f172a_42%,#020617_100%)] px-4 py-8 text-white">
      <div className="mx-auto max-w-5xl">
        <Link href="/" className="inline-flex items-center gap-2 text-slate-300 transition hover:text-white">
          <ArrowLeft className="size-5" />
          홈으로
        </Link>

        <header className="mt-6 rounded-3xl border border-white/10 bg-white/8 p-6">
          <p className="flex items-center gap-2 text-cyan-300">
            <BookOpen className="size-5" />
            DB 기반 문제 풀이
          </p>
          <h1 className="mt-2 text-4xl font-black">패턴별 훈련장</h1>
          <p className="mt-3 text-slate-300">원하는 차트 패턴을 골라 해당 패턴 문제만 연습합니다.</p>
        </header>

        {hasApiError ? (
          <section className="mt-8 rounded-2xl border border-yellow-400/30 bg-yellow-950/30 p-8">
            <h2 className="text-2xl font-black text-yellow-100">패턴 데이터를 불러오지 못했습니다.</h2>
            <p className="mt-3 text-yellow-50">백엔드 배포 주소, Vercel 환경변수, Supabase 연결 상태를 확인해주세요.</p>
          </section>
        ) : (
          <section className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {patterns.map((pattern, index) => (
              <Link
                key={pattern.slug}
                href={`/play?pattern=${encodeURIComponent(pattern.slug)}`}
                className="rounded-2xl border border-white/10 bg-white/8 p-6 transition hover:border-cyan-300/50 hover:bg-white/10"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-bold text-cyan-300">{index + 1}번 패턴</p>
                    <h2 className="mt-2 text-2xl font-black">{pattern.name}</h2>
                  </div>
                  <ChevronRight className="mt-1 size-6 text-slate-400" />
                </div>
                <div className="mt-6 rounded-xl border border-white/10 bg-slate-950/40 p-4">
                  <p className="text-sm text-slate-400">등록된 문제</p>
                  <p className={pattern.questionCount > 0 ? "mt-1 text-3xl font-black text-cyan-300" : "mt-1 text-3xl font-black text-slate-500"}>
                    {pattern.questionCount}문제
                  </p>
                </div>
                <p className="mt-5 text-sm text-slate-300">
                  {pattern.questionCount > 0 ? "훈련 시작하기" : "문제 seed 추가 필요"}
                </p>
              </Link>
            ))}
          </section>
        )}
      </div>
    </main>
  );
}
