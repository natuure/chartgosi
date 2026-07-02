import Link from "next/link";
import { ArrowLeft, BarChart3, ChevronRight, History } from "lucide-react";
import { LoginRequired } from "@/components/login-required";
import { getRecentTrainingSessions } from "@/lib/api";
import { getServerAccessToken } from "@/lib/server-auth";
import type { TrainingSessionSummary } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function TrainingHistoryPage() {
  const accessToken = await getServerAccessToken();
  let sessions: TrainingSessionSummary[] = [];
  let hasApiError = false;

  if (!accessToken) {
    return <PageShell><LoginRequired nextPath="/training-history" title="최근 훈련 기록은 로그인이 필요합니다" /></PageShell>;
  }

  try {
    const response = await getRecentTrainingSessions(20, accessToken);
    sessions = response.items;
  } catch {
    hasApiError = true;
  }

  return (
    <PageShell>
      <header className="mt-6 rounded-3xl border border-white/10 bg-white/8 p-6">
        <p className="flex items-center gap-2 text-cyan-300">
          <History className="size-5" />
          최근 훈련 기록
        </p>
        <h1 className="mt-2 text-4xl font-black">내가 푼 패턴 세션</h1>
        <p className="mt-3 text-slate-300">연속 훈련에서 제출한 답안을 세션별로 다시 확인합니다.</p>
      </header>

      {hasApiError ? (
        <section className="mt-8 rounded-2xl border border-yellow-400/30 bg-yellow-950/30 p-8">
          <h2 className="text-2xl font-black text-yellow-100">훈련 기록을 불러오지 못했습니다</h2>
          <p className="mt-3 text-yellow-50">로그인 상태와 백엔드 배포 주소를 확인해주세요.</p>
        </section>
      ) : sessions.length === 0 ? (
        <section className="mt-8 rounded-2xl border border-white/10 bg-white/8 p-8">
          <BarChart3 className="size-10 text-slate-400" />
          <h2 className="mt-4 text-2xl font-black">아직 저장된 훈련 세션이 없습니다</h2>
          <p className="mt-3 text-slate-300">패턴별 훈련장에서 1세트를 끝내면 여기에 기록됩니다.</p>
          <Link href="/patterns" className="mt-6 inline-block rounded-xl bg-cyan-400 px-5 py-3 font-black text-slate-950">
            패턴 훈련 시작하기
          </Link>
        </section>
      ) : (
        <section className="mt-8 grid gap-4">
          {sessions.map((session) => (
            <Link
              key={session.sessionId}
              href={`/training-history/${encodeURIComponent(session.sessionId)}`}
              className="grid gap-4 rounded-2xl border border-white/10 bg-white/8 p-5 transition hover:border-cyan-300/60 md:grid-cols-[1fr_120px_120px_40px]"
            >
              <div>
                <p className="text-sm font-bold text-cyan-300">{session.pattern.name}</p>
                <h2 className="mt-1 text-2xl font-black">{formatDateTime(session.lastAnsweredAt)}</h2>
                <p className="mt-2 text-sm text-slate-400">시작: {formatDateTime(session.startedAt)}</p>
              </div>
              <Metric label="문제" value={`${session.solvedCount}`} />
              <Metric label="정답률" value={`${Math.round(session.accuracy * 100)}%`} />
              <ChevronRight className="self-center text-slate-400" />
            </Link>
          ))}
        </section>
      )}
    </PageShell>
  );
}

function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,#172554_0%,#0f172a_42%,#020617_100%)] px-4 py-8 text-white">
      <div className="mx-auto max-w-5xl">
        <Link href="/me" className="inline-flex items-center gap-2 text-slate-300 transition hover:text-white">
          <ArrowLeft className="size-5" />
          내 정보로
        </Link>
        {children}
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-slate-950/30 p-4">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-black text-white">{value}</p>
    </div>
  );
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
