import Link from "next/link";
import { ArrowLeft, BarChart3, Sparkles } from "lucide-react";
import { AiReportGenerateButton } from "@/components/ai-report-generate-button";
import { LoginRequired } from "@/components/login-required";
import { ApiRequestError, getLatestAiReport } from "@/lib/api";
import { formatApiError } from "@/lib/api-errors";
import { getServerAccessToken } from "@/lib/server-auth";
import type { AiReport } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function AiReportPage() {
  const accessToken = await getServerAccessToken();
  let report: AiReport | null = null;
  let apiError: string | null = null;

  if (!accessToken) {
    return (
      <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,#312e81_0%,#0f172a_42%,#020617_100%)] px-4 py-8 text-white">
        <div className="mx-auto max-w-5xl">
          <Link href="/" className="inline-flex items-center gap-2 text-slate-300 transition hover:text-white">
            <ArrowLeft className="size-5" />
            홈으로
          </Link>
          <LoginRequired nextPath="/ai-report" title="AI 리포트 확인에는 로그인이 필요합니다." />
        </div>
      </main>
    );
  }

  try {
    report = await getLatestAiReport(accessToken);
  } catch (error) {
    if (error instanceof ApiRequestError && error.status === 404) {
      report = null;
    } else {
      apiError = formatApiError("AI 리포트", error);
    }
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,#312e81_0%,#0f172a_42%,#020617_100%)] px-4 py-8 text-white">
      <div className="mx-auto max-w-5xl">
        <Link href="/" className="inline-flex items-center gap-2 text-slate-300 transition hover:text-white">
          <ArrowLeft className="size-5" />
          홈으로
        </Link>

        <header className="mt-6 flex flex-col gap-4 rounded-3xl border border-white/10 bg-white/8 p-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="flex items-center gap-2 text-fuchsia-300">
              <Sparkles className="size-5" />
              AI 분석 리포트
            </p>
            <h1 className="mt-2 text-4xl font-black">차트 실력 분석</h1>
            <p className="mt-3 text-slate-300">최근 30일 답안 기록을 규칙 기반으로 분석합니다.</p>
          </div>
          <AiReportGenerateButton label={report ? "리포트 다시 생성" : "리포트 생성"} />
        </header>

        {apiError ? (
          <section className="mt-8 rounded-2xl border border-yellow-400/30 bg-yellow-950/30 p-8">
            <h2 className="text-2xl font-black text-yellow-100">AI 리포트를 불러오지 못했습니다.</h2>
            <p className="mt-3 text-yellow-50">{apiError}</p>
            <p className="mt-3 text-sm text-yellow-100">401이면 인증 환경변수, 500이면 Render 로그와 DATABASE_URL/DB 테이블 상태를 확인해주세요.</p>
          </section>
        ) : !report ? (
          <section className="mt-8 rounded-2xl border border-white/10 bg-white/8 p-8">
            <BarChart3 className="size-12 text-slate-400" />
            <h2 className="mt-5 text-2xl font-black">아직 생성된 리포트가 없습니다.</h2>
            <p className="mt-3 text-slate-300">문제를 몇 개 풀고 리포트를 생성하면 패턴별 약점을 볼 수 있습니다.</p>
          </section>
        ) : report ? (
          <>
            <section className="mt-8 grid gap-4 lg:grid-cols-[280px_1fr]">
              <div className="rounded-2xl border border-white/10 bg-white/8 p-6 text-center">
                <p className="text-slate-300">종합 점수</p>
                <p className="mt-4 text-6xl font-black text-fuchsia-300">{report.overallScore ?? 0}</p>
                <p className="mt-4 text-slate-400">최근 {report.answerCount}문제 기준</p>
                <p className="mt-1 text-slate-400">{report.periodStart} ~ {report.periodEnd}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/8 p-6">
                <h2 className="text-2xl font-black">AI 코멘트</h2>
                <p className="mt-4 leading-8 text-slate-200">{report.summary}</p>
                <div className="mt-6 grid gap-3 sm:grid-cols-3">
                  <Metric label="추세 읽기" value={report.traitScores?.trend_reading ?? 0} />
                  <Metric label="속도 조절" value={report.traitScores?.speed_control ?? 0} />
                  <Metric label="일관성" value={report.traitScores?.consistency ?? 0} />
                </div>
              </div>
            </section>

            <section className="mt-8 rounded-2xl border border-white/10 bg-white/8 p-6">
              <h2 className="text-2xl font-black">패턴별 정답률</h2>
              <div className="mt-6 space-y-4">
                {Object.entries(report.patternAccuracy ?? {}).map(([slug, item]) => (
                  <div key={slug}>
                    <div className="mb-2 flex justify-between text-sm">
                      <span className="font-bold">{item.name}</span>
                      <span className="text-cyan-300">{Math.round(item.accuracy * 100)}%</span>
                    </div>
                    <div className="h-3 rounded-full bg-slate-800">
                      <div className="h-3 rounded-full bg-gradient-to-r from-fuchsia-500 to-cyan-300" style={{ width: `${Math.round(item.accuracy * 100)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="mt-8 grid gap-3 sm:grid-cols-2">
              {(report.recommendations ?? []).map((recommendation) => (
                <Link
                  key={recommendation.href}
                  href={recommendation.href}
                  className="rounded-2xl border border-white/10 bg-white/8 p-6 transition hover:border-cyan-300/50"
                >
                  <h3 className="text-xl font-black">{recommendation.title}</h3>
                  <p className="mt-2 text-slate-300">{recommendation.description}</p>
                </Link>
              ))}
            </section>
          </>
        ) : null}
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
      <p className="text-sm text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-black">{value}</p>
    </div>
  );
}
