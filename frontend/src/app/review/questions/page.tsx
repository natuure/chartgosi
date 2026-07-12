import Link from "next/link";
import { ArrowLeft, ClipboardCheck } from "lucide-react";
import { LoginRequired } from "@/components/login-required";
import { QuestionReviewCard } from "@/components/question-review-card";
import { getPatterns, getReviewQuestions } from "@/lib/api";
import { formatApiError } from "@/lib/api-errors";
import { getServerAccessToken } from "@/lib/server-auth";
import type { Pattern, ReviewStatus } from "@/lib/types";

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
  let reviewResponse = null;
  let apiError: string | null = null;
  const reviewStatus = toReviewStatus(status);

  try {
    const [patternItems, questions] = await Promise.all([
      getPatterns(),
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
