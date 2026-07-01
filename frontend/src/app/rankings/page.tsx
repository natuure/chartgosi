import Link from "next/link";
import { ArrowLeft, Medal, Trophy } from "lucide-react";
import { getMyRanking, getRankings } from "@/lib/api";
import type { MyRanking, RankingItem, RankingPeriodType } from "@/lib/types";

export const dynamic = "force-dynamic";

const periods: Array<{ label: string; value: RankingPeriodType }> = [
  { label: "일간", value: "daily" },
  { label: "주간", value: "weekly" },
  { label: "월간", value: "monthly" },
  { label: "전체", value: "all_time" },
];

export default async function RankingsPage({
  searchParams,
}: {
  searchParams: Promise<{ period_type?: string }>;
}) {
  const params = await searchParams;
  const periodType = parsePeriodType(params.period_type);
  let rankings: RankingItem[] = [];
  let myRanking: MyRanking | null = null;
  let hasApiError = false;

  try {
    const [rankingResponse, myRankingResponse] = await Promise.all([
      getRankings(periodType),
      getMyRanking(periodType),
    ]);
    rankings = rankingResponse.items;
    myRanking = myRankingResponse;
  } catch {
    hasApiError = true;
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,#1e3a8a_0%,#0f172a_38%,#020617_100%)] px-4 py-8 text-white">
      <div className="mx-auto max-w-5xl">
        <Link href="/" className="inline-flex items-center gap-2 text-slate-300 transition hover:text-white">
          <ArrowLeft className="size-5" />
          홈으로
        </Link>

        <header className="mt-6 rounded-3xl border border-white/10 bg-white/8 p-6">
          <p className="flex items-center gap-2 text-yellow-300">
            <Trophy className="size-5" />
            실시간 집계
          </p>
          <h1 className="mt-2 text-4xl font-black">랭킹</h1>
          <p className="mt-3 text-slate-300">정답 수와 풀이 수를 기준으로 점수를 계산합니다.</p>

          <nav className="mt-6 flex flex-wrap gap-2">
            {periods.map((period) => (
              <Link
                key={period.value}
                href={`/rankings?period_type=${period.value}`}
                className={
                  period.value === periodType
                    ? "rounded-full bg-cyan-400 px-4 py-2 font-black text-slate-950"
                    : "rounded-full border border-white/10 px-4 py-2 font-bold text-slate-300"
                }
              >
                {period.label}
              </Link>
            ))}
          </nav>
        </header>

        {hasApiError ? (
          <section className="mt-8 rounded-2xl border border-yellow-400/30 bg-yellow-950/30 p-8">
            <h2 className="text-2xl font-black text-yellow-100">랭킹 데이터를 불러오지 못했습니다.</h2>
            <p className="mt-3 text-yellow-50">백엔드 배포 주소와 Supabase 연결 상태를 확인해주세요.</p>
            <Link href="/play" className="mt-6 inline-block rounded-xl bg-cyan-400 px-5 py-3 font-black text-slate-950">
              문제 풀기
            </Link>
          </section>
        ) : (
          <>
            {myRanking ? (
              <section className="mt-8 grid gap-4 rounded-2xl border border-cyan-300/20 bg-cyan-300/10 p-6 sm:grid-cols-4">
                <Metric label="내 순위" value={myRanking.rank ? `#${myRanking.rank}` : "-"} />
                <Metric label="점수" value={`${myRanking.score}점`} />
                <Metric label="정답률" value={`${Math.round(myRanking.accuracy * 100)}%`} />
                <Metric label="풀이 수" value={`${myRanking.solvedCount}문제`} />
              </section>
            ) : null}

            <section className="mt-8 overflow-hidden rounded-2xl border border-white/10 bg-white/8">
              {rankings.length === 0 ? (
                <div className="p-8">
                  <Medal className="size-12 text-slate-400" />
                  <h2 className="mt-5 text-2xl font-black">아직 랭킹 데이터가 없습니다.</h2>
                  <p className="mt-3 text-slate-300">문제를 풀면 랭킹에 자동으로 반영됩니다.</p>
                  <Link href="/play" className="mt-6 inline-block rounded-xl bg-cyan-400 px-5 py-3 font-black text-slate-950">
                    첫 문제 풀기
                  </Link>
                </div>
              ) : (
                rankings.map((user) => (
                  <div
                    key={user.userId}
                    className="grid grid-cols-[64px_1fr] gap-4 border-b border-white/10 p-5 last:border-b-0 sm:grid-cols-[80px_1fr_120px_120px_120px]"
                  >
                    <strong className={user.rank <= 3 ? "text-yellow-300" : "text-cyan-300"}>#{user.rank}</strong>
                    <span className="font-bold">{user.nickname}</span>
                    <span>{user.score}점</span>
                    <span>{Math.round(user.accuracy * 100)}%</span>
                    <span>{user.solvedCount}문제</span>
                  </div>
                ))
              )}
            </section>
          </>
        )}
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-sm text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-black">{value}</p>
    </div>
  );
}

function parsePeriodType(value?: string): RankingPeriodType {
  if (value === "daily" || value === "weekly" || value === "monthly" || value === "all_time") {
    return value;
  }
  return "weekly";
}
