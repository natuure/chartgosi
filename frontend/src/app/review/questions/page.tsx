import Link from "next/link";
import { AlertTriangle, ArrowLeft, ClipboardCheck, CheckCircle2 } from "lucide-react";
import { LoginRequired } from "@/components/login-required";
import { QuestionReviewCard } from "@/components/question-review-card";
import { getPatterns, getReviewDashboard, getReviewQuestions } from "@/lib/api";
import { formatApiError } from "@/lib/api-errors";
import { getServerAccessToken } from "@/lib/server-auth";
import type { Pattern, ReviewDashboardResponse, ReviewStatus } from "@/lib/types";

export const dynamic = "force-dynamic";

const reviewStatuses: Array<{ value: ReviewStatus | "all"; label: string }> = [
  { value: "all", label: "전체" },
  { value: "pending", label: "대기" },
  { value: "approved", label: "좋음" },
  { value: "needs_review", label: "애매함" },
  { value: "rejected", label: "제외" },
];

export default async function QuestionReviewPage({
  searchParams,
}: {
  searchParams: Promise<{ pattern?: string; status?: string }>;
}) {
  const { pattern, status } = await searchParams;
  const accessToken = await getServerAccessToken();
  const nextPath = `/review/questions${toQuery(pattern, status)}`;

  if (!accessToken) {
    return (
      <main className="min-h-screen bg-slate-950 px-4 py-8 text-white">
        <div className="mx-auto max-w-6xl">
          <LoginRequired nextPath={nextPath} title="문제 검수 화면은 로그인이 필요합니다." />
        </div>
      </main>
    );
  }

  let patterns: Pattern[] = [];
  let dashboard: ReviewDashboardResponse | null = null;
  let reviewResponse = null;
  let apiError: string | null = null;
  const reviewStatus = toReviewStatus(status);

  try {
    const [patternItems, dashboardResponse, questions] = await Promise.all([
      getPatterns(),
      getReviewDashboard(accessToken),
      getReviewQuestions(
        {
          patternSlug: pattern,
          reviewStatus,
          limit: 20,
          offset: 0,
        },
        accessToken,
      ),
    ]);
    patterns = patternItems;
    dashboard = dashboardResponse;
    reviewResponse = questions;
  } catch (error) {
    apiError = formatApiError("문제 검수 조회", error);
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,#164e63_0%,#0f172a_38%,#020617_100%)] px-4 py-8 text-white">
      <div className="mx-auto max-w-7xl">
        <Link href="/" className="inline-flex items-center gap-2 text-slate-300 transition hover:text-white">
          <ArrowLeft className="size-5" />
          홈으로
        </Link>

        <header className="mt-6 rounded-3xl border border-white/10 bg-white/8 p-6">
          <p className="flex items-center gap-2 text-cyan-300">
            <ClipboardCheck className="size-5" />
            내부 검수
          </p>
          <h1 className="mt-2 text-4xl font-black">문제 검수 / 패턴 마커</h1>
          <p className="mt-3 max-w-3xl text-slate-300">
            실제 출제 문제를 차트, 정답, 스코어 근거와 함께 확인하고 좋음/애매함/제외 상태와 핵심 지점 마커를 저장합니다.
          </p>
        </header>

        <section className="mt-6 flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/8 p-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap gap-2">
            <FilterLink href="/review/questions" active={!pattern}>
              모든 패턴
            </FilterLink>
            {patterns.map((item) => (
              <FilterLink key={item.slug} href={`/review/questions?pattern=${encodeURIComponent(item.slug)}${status ? `&status=${encodeURIComponent(status)}` : ""}`} active={pattern === item.slug}>
                {item.name}
              </FilterLink>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            {reviewStatuses.map((item) => (
              <FilterLink key={item.value} href={`/review/questions${toQuery(pattern, item.value === "all" ? undefined : item.value)}`} active={(item.value === "all" && !reviewStatus) || reviewStatus === item.value}>
                {item.label}
              </FilterLink>
            ))}
          </div>
        </section>

        {dashboard ? <ReviewDashboard dashboard={dashboard} selectedPattern={pattern} /> : null}

        {apiError ? (
          <section className="mt-8 rounded-2xl border border-red-400/30 bg-red-950/30 p-6">
            <h2 className="text-2xl font-black text-red-100">검수 문제를 불러오지 못했습니다.</h2>
            <p className="mt-3 text-red-50">{apiError}</p>
          </section>
        ) : null}

        {reviewResponse ? (
          <section className="mt-8 space-y-5">
            <p className="text-sm font-bold text-slate-300">
              총 {reviewResponse.total}개 중 {reviewResponse.items.length}개 표시
            </p>
            {reviewResponse.items.map((question) => (
              <QuestionReviewCard key={question.id} question={question} />
            ))}
            {reviewResponse.items.length === 0 ? (
              <div className="rounded-2xl border border-white/10 bg-white/8 p-8 text-center text-slate-300">
                조건에 맞는 검수 대상 문제가 없습니다.
              </div>
            ) : null}
          </section>
        ) : null}
      </div>
    </main>
  );
}

function ReviewDashboard({ dashboard, selectedPattern }: { dashboard: ReviewDashboardResponse; selectedPattern?: string }) {
  const selected = selectedPattern ? dashboard.items.find((item) => item.pattern.slug === selectedPattern) : null;
  const items = selected ? [selected] : dashboard.items;
  const shortageItems = dashboard.items.filter((item) => item.approvedShortage > 0);
  const totalApproved = dashboard.items.reduce((sum, item) => sum + item.approvedCount, 0);
  const totalPlayable = dashboard.items.reduce((sum, item) => sum + item.playableCount, 0);
  const totalWarnings = dashboard.items.reduce((sum, item) => sum + item.markerWarningCount, 0);

  return (
    <section className="mt-6 space-y-4">
      <div className="grid gap-3 md:grid-cols-3">
        <DashboardMetric label="승인 문제" value={`${totalApproved}개`} helper={`패턴당 목표 ${dashboard.approvedTarget}개`} />
        <DashboardMetric label="출제 가능 후보" value={`${totalPlayable}개`} helper="rejected 제외 + 필수 마커 충족" />
        <DashboardMetric label="마커 경고" value={`${totalWarnings}개`} helper="필수 마커 누락 문제" tone={totalWarnings > 0 ? "warning" : "ok"} />
      </div>

      {shortageItems.length > 0 ? (
        <div className="rounded-2xl border border-yellow-300/30 bg-yellow-950/30 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 size-5 shrink-0 text-yellow-200" />
            <div>
              <h2 className="font-black text-yellow-100">출제 후보 부족 경고</h2>
              <p className="mt-1 text-sm text-yellow-50/80">
                승인 문제가 패턴당 {dashboard.approvedTarget}개 미만인 패턴이 있습니다. 실제 출제 품질을 안정화하려면 부족분을 먼저 검수하세요.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {shortageItems.map((item) => (
                  <Link
                    key={item.pattern.slug}
                    href={`/review/questions?pattern=${encodeURIComponent(item.pattern.slug)}&status=pending`}
                    className="rounded-full border border-yellow-200/30 bg-yellow-300/10 px-3 py-1 text-xs font-black text-yellow-50 transition hover:border-yellow-100"
                  >
                    {item.pattern.name} {item.approvedCount}/{item.approvedTarget} · {item.approvedShortage}개 부족
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-2xl border border-emerald-300/20 bg-emerald-950/20 p-4">
          <div className="flex items-center gap-2 text-sm font-black text-emerald-100">
            <CheckCircle2 className="size-5" />
            모든 패턴이 승인 문제 목표를 채웠습니다.
          </div>
        </div>
      )}

      <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/8">
        <div className="border-b border-white/10 p-4">
          <h2 className="font-black text-cyan-100">{selected ? `${selected.pattern.name} 검수 현황` : "패턴별 검수 완료율"}</h2>
          <p className="mt-1 text-sm text-slate-400">전체/좋음/애매함/제외/마커 경고 수를 기준으로 다음 검수 대상을 고릅니다.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-slate-950/60 text-xs text-slate-400">
              <tr>
                <th className="px-4 py-3">패턴</th>
                <th className="px-4 py-3">전체</th>
                <th className="px-4 py-3">좋음</th>
                <th className="px-4 py-3">대기</th>
                <th className="px-4 py-3">애매함</th>
                <th className="px-4 py-3">제외</th>
                <th className="px-4 py-3">마커 경고</th>
                <th className="px-4 py-3">출제 가능</th>
                <th className="px-4 py-3">목표</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.pattern.slug} className="border-t border-white/5">
                  <td className="px-4 py-3 font-black text-white">
                    <Link href={`/review/questions?pattern=${encodeURIComponent(item.pattern.slug)}`} className="hover:text-cyan-200">
                      {item.pattern.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-300">{item.totalCount}</td>
                  <td className="px-4 py-3 font-bold text-emerald-200">{item.approvedCount}</td>
                  <td className="px-4 py-3 text-slate-300">{item.pendingCount}</td>
                  <td className="px-4 py-3 text-yellow-100">{item.needsReviewCount}</td>
                  <td className="px-4 py-3 text-red-200">{item.rejectedCount}</td>
                  <td className={item.markerWarningCount > 0 ? "px-4 py-3 font-bold text-yellow-100" : "px-4 py-3 text-slate-400"}>{item.markerWarningCount}</td>
                  <td className="px-4 py-3 text-cyan-100">{item.playableCount}</td>
                  <td className="px-4 py-3">
                    {item.approvedShortage > 0 ? (
                      <span className="rounded-full bg-yellow-300/15 px-2 py-1 text-xs font-black text-yellow-100">{item.approvedShortage}개 부족</span>
                    ) : (
                      <span className="rounded-full bg-emerald-300/15 px-2 py-1 text-xs font-black text-emerald-100">충족</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

function DashboardMetric({ label, value, helper, tone = "default" }: { label: string; value: string; helper: string; tone?: "default" | "warning" | "ok" }) {
  const toneClass =
    tone === "warning"
      ? "border-yellow-300/30 bg-yellow-950/25 text-yellow-100"
      : tone === "ok"
        ? "border-emerald-300/20 bg-emerald-950/20 text-emerald-100"
        : "border-white/10 bg-white/8 text-white";

  return (
    <div className={`rounded-2xl border p-4 ${toneClass}`}>
      <p className="text-sm text-slate-300">{label}</p>
      <p className="mt-2 text-3xl font-black">{value}</p>
      <p className="mt-1 text-xs text-slate-400">{helper}</p>
    </div>
  );
}

function FilterLink({ href, active, children }: { href: string; active: boolean; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className={active ? "rounded-full bg-cyan-400 px-4 py-2 text-sm font-black text-slate-950" : "rounded-full border border-white/10 bg-slate-950/40 px-4 py-2 text-sm font-bold text-slate-200 transition hover:border-cyan-300/60"}
    >
      {children}
    </Link>
  );
}

function toReviewStatus(value?: string): ReviewStatus | undefined {
  if (value === "pending" || value === "approved" || value === "needs_review" || value === "rejected") {
    return value;
  }
  return undefined;
}

function toQuery(pattern?: string, status?: string) {
  const params = new URLSearchParams();
  if (pattern) {
    params.set("pattern", pattern);
  }
  if (status) {
    params.set("status", status);
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}
