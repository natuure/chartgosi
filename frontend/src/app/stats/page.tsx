import Link from "next/link";
import { ArrowLeft, BarChart3, Clock, Target, XCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { LoginRequired } from "@/components/login-required";
import { getMyStats } from "@/lib/api";
import { getServerAccessToken } from "@/lib/server-auth";
import type { MyStats } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function StatsPage() {
  const accessToken = await getServerAccessToken();
  let stats: MyStats | null = null;
  let hasApiError = false;

  if (!accessToken) {
    return <PageShell><LoginRequired nextPath="/stats" title="통계 확인에는 로그인이 필요합니다." /></PageShell>;
  }

  try {
    stats = await getMyStats(accessToken);
  } catch {
    hasApiError = true;
  }

  return (
    <PageShell>
      <header className="mt-6 rounded-3xl border border-white/10 bg-white/8 p-6">
        <p className="flex items-center gap-2 text-teal-300">
          <BarChart3 className="size-5" />
          나의 풀이 데이터
        </p>
        <h1 className="mt-2 text-4xl font-black">통계</h1>
        <p className="mt-3 text-slate-300">내 답안 기록을 기반으로 정답률과 패턴별 약점을 확인합니다.</p>
      </header>

      {hasApiError ? (
        <section className="mt-8 rounded-2xl border border-yellow-400/30 bg-yellow-950/30 p-8">
          <h2 className="text-2xl font-black text-yellow-100">통계 데이터를 불러오지 못했습니다.</h2>
          <p className="mt-3 text-yellow-50">로그인 세션, 백엔드 배포 주소, Supabase 연결 상태를 확인해주세요.</p>
          <Link href="/play" className="mt-6 inline-block rounded-xl bg-cyan-400 px-5 py-3 font-black text-slate-950">
            문제 풀기
          </Link>
        </section>
      ) : stats && stats.solvedCount > 0 ? (
        <>
          <section className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Metric icon={Target} label="전체 풀이" value={`${stats.solvedCount}문제`} />
            <Metric icon={BarChart3} label="정답률" value={`${Math.round(stats.accuracy * 100)}%`} />
            <Metric icon={XCircle} label="오답" value={`${stats.wrongCount}문제`} />
            <Metric icon={Clock} label="평균 풀이 시간" value={formatDuration(stats.averageDurationMs)} />
          </section>

          <section className="mt-8 rounded-2xl border border-white/10 bg-white/8 p-6">
            <h2 className="text-2xl font-black">패턴별 정답률</h2>
            <div className="mt-6 space-y-5">
              {stats.patternStats.map((item) => (
                <div key={item.pattern.id}>
                  <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-sm">
                    <div>
                      <p className="font-bold text-white">{item.pattern.name}</p>
                      <p className="text-slate-400">{item.correctCount}/{item.solvedCount} 정답</p>
                    </div>
                    <strong className="text-cyan-300">{Math.round(item.accuracy * 100)}%</strong>
                  </div>
                  <div className="h-3 rounded-full bg-slate-800">
                    <div
                      className="h-3 rounded-full bg-gradient-to-r from-teal-400 to-cyan-300"
                      style={{ width: `${Math.round(item.accuracy * 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>
        </>
      ) : (
        <section className="mt-8 rounded-2xl border border-white/10 bg-white/8 p-8">
          <BarChart3 className="size-12 text-slate-400" />
          <h2 className="mt-5 text-2xl font-black">아직 통계 데이터가 없습니다.</h2>
          <p className="mt-3 text-slate-300">문제를 풀면 풀이 수, 정답률, 패턴별 통계가 자동으로 쌓입니다.</p>
          <Link href="/play" className="mt-6 inline-block rounded-xl bg-cyan-400 px-5 py-3 font-black text-slate-950">
            첫 문제 풀기
          </Link>
        </section>
      )}
    </PageShell>
  );
}

function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,#134e4a_0%,#0f172a_40%,#020617_100%)] px-4 py-8 text-white">
      <div className="mx-auto max-w-5xl">
        <Link href="/" className="inline-flex items-center gap-2 text-slate-300 transition hover:text-white">
          <ArrowLeft className="size-5" />
          홈으로
        </Link>
        {children}
      </div>
    </main>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/8 p-6">
      <Icon className="size-7 text-cyan-300" />
      <p className="mt-4 text-sm text-slate-400">{label}</p>
      <p className="mt-1 text-3xl font-black">{value}</p>
    </div>
  );
}

function formatDuration(value: number | null) {
  if (!value) {
    return "-";
  }
  return `${Math.round(value / 1000)}초`;
}
