import Link from "next/link";
import { ArrowLeft, Crown, Heart, History, UserCircle } from "lucide-react";
import { LoginRequired } from "@/components/login-required";
import { getFavorites, getSubscription } from "@/lib/api";
import { formatApiError } from "@/lib/api-errors";
import { getServerAccessToken } from "@/lib/server-auth";
import type { FavoriteQuestionItem, Subscription } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function MePage() {
  const accessToken = await getServerAccessToken();
  let subscription: Subscription | null = null;
  let favorites: FavoriteQuestionItem[] = [];
  const apiErrors: string[] = [];

  if (!accessToken) {
    return <PageShell><LoginRequired nextPath="/me" title="내 정보 확인에는 로그인이 필요합니다" /></PageShell>;
  }

  const [subscriptionResult, favoritesResult] = await Promise.allSettled([
    getSubscription(accessToken),
    getFavorites(accessToken),
  ]);

  if (subscriptionResult.status === "fulfilled") {
    subscription = subscriptionResult.value;
  } else {
    apiErrors.push(formatApiError("구독 상태", subscriptionResult.reason));
  }

  if (favoritesResult.status === "fulfilled") {
    favorites = favoritesResult.value.items;
  } else {
    apiErrors.push(formatApiError("즐겨찾기", favoritesResult.reason));
  }

  return (
    <PageShell>
      <header className="mt-6 rounded-3xl border border-white/10 bg-white/8 p-6">
        <p className="flex items-center gap-2 text-cyan-300">
          <UserCircle className="size-5" />
          내 정보
        </p>
        <h1 className="mt-2 text-4xl font-black">차트고시 프로필</h1>
        <p className="mt-3 text-slate-300">내 계정의 구독 상태, 즐겨찾기 문제, 최근 훈련 기록을 확인합니다.</p>
      </header>

      {apiErrors.length > 0 ? (
        <section className="mt-8 rounded-2xl border border-yellow-400/30 bg-yellow-950/30 p-8">
          <h2 className="text-2xl font-black text-yellow-100">내 정보를 불러오지 못했습니다</h2>
          <p className="mt-3 text-yellow-50">아래 상태를 보면 Render 백엔드에서 어떤 요청이 실패했는지 확인할 수 있습니다.</p>
          <div className="mt-5 space-y-2">
            {apiErrors.map((error) => (
              <p key={error} className="rounded-xl border border-yellow-400/20 bg-slate-950/40 p-3 text-sm text-yellow-50">
                {error}
              </p>
            ))}
          </div>
          <p className="mt-5 text-sm text-yellow-100">
            401이면 Render의 SUPABASE_JWT_SECRET 또는 토큰 검증 설정을, 500이면 Render 로그와 DATABASE_URL/DB 테이블 상태를 확인해야 합니다.
          </p>
        </section>
      ) : (
        <>
          <section className="mt-8 grid gap-4 sm:grid-cols-4">
            <Metric label="플랜" value={subscription?.plan.toUpperCase() ?? "-"} />
            <Metric label="상태" value={subscription?.status ?? "-"} />
            <Metric label="오늘 남은 문제" value={`${subscription?.remainingToday ?? 0}/${subscription?.dailyQuestionLimit ?? 0}`} />
            <Metric label="연속 퀴즈" value={`${subscription?.streakDays ?? 0}일`} />
          </section>

          <section className="mt-8 rounded-2xl border border-cyan-300/20 bg-cyan-950/20 p-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="flex items-center gap-2 text-cyan-300">
                  <History className="size-5" />
                  훈련 기록
                </p>
                <h2 className="mt-2 text-2xl font-black">최근 패턴 훈련 다시 보기</h2>
                <p className="mt-2 text-slate-300">완료한 연속 훈련 세션의 정답률과 문제별 해설을 확인합니다.</p>
              </div>
              <Link href="/training-history" className="rounded-xl bg-cyan-400 px-5 py-3 text-center font-black text-slate-950">
                기록 보기
              </Link>
            </div>
          </section>

          <section className="mt-8 rounded-2xl border border-white/10 bg-white/8 p-6">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="flex items-center gap-2 text-yellow-300">
                  <Heart className="size-5" />
                  즐겨찾기
                </p>
                <h2 className="mt-2 text-2xl font-black">다시 풀 문제</h2>
              </div>
              <Link href="/play" className="rounded-xl bg-cyan-400 px-4 py-2 font-black text-slate-950">
                문제 풀기
              </Link>
            </div>

            {favorites.length === 0 ? (
              <div className="mt-6 rounded-2xl border border-white/10 bg-slate-950/40 p-6">
                <Crown className="size-10 text-slate-400" />
                <h3 className="mt-4 text-xl font-black">아직 즐겨찾기한 문제가 없습니다</h3>
                <p className="mt-2 text-slate-300">문제 화면에서 별표를 누르면 여기에 저장됩니다.</p>
              </div>
            ) : (
              <div className="mt-6 grid gap-3">
                {favorites.map((favorite) => (
                  <Link
                    key={favorite.id}
                    href={`/play?question_id=${encodeURIComponent(favorite.question.id)}&retry=1`}
                    className="rounded-2xl border border-white/10 bg-slate-950/40 p-5 transition hover:border-cyan-300/50"
                  >
                    <p className="text-sm font-bold text-cyan-300">{favorite.question.pattern.name} · {favorite.question.difficultyLabel}</p>
                    <h3 className="mt-2 text-xl font-black">기준일 {favorite.question.baseDate} 문제 다시 풀기</h3>
                    <p className="mt-2 text-sm text-slate-400">저장일 {formatDate(favorite.createdAt)}</p>
                  </Link>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </PageShell>
  );
}

function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,#172554_0%,#0f172a_42%,#020617_100%)] px-4 py-8 text-white">
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

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/8 p-5">
      <p className="text-sm text-slate-400">{label}</p>
      <p className="mt-2 text-2xl font-black">{value}</p>
    </div>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium" }).format(new Date(value));
}
