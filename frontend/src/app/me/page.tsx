import Link from "next/link";
import { ArrowLeft, Crown, Heart, UserCircle } from "lucide-react";
import { getFavorites, getSubscription } from "@/lib/api";
import type { FavoriteQuestionItem, Subscription } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function MePage() {
  let subscription: Subscription | null = null;
  let favorites: FavoriteQuestionItem[] = [];
  let hasApiError = false;

  try {
    const [subscriptionResponse, favoritesResponse] = await Promise.all([
      getSubscription(),
      getFavorites(),
    ]);
    subscription = subscriptionResponse;
    favorites = favoritesResponse.items;
  } catch {
    hasApiError = true;
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,#172554_0%,#0f172a_42%,#020617_100%)] px-4 py-8 text-white">
      <div className="mx-auto max-w-5xl">
        <Link href="/" className="inline-flex items-center gap-2 text-slate-300 transition hover:text-white">
          <ArrowLeft className="size-5" />
          홈으로
        </Link>

        <header className="mt-6 rounded-3xl border border-white/10 bg-white/8 p-6">
          <p className="flex items-center gap-2 text-cyan-300">
            <UserCircle className="size-5" />
            내 정보
          </p>
          <h1 className="mt-2 text-4xl font-black">차트고시 프로필</h1>
          <p className="mt-3 text-slate-300">MVP에서는 seed 개발 사용자 기준으로 구독 상태와 즐겨찾기를 확인합니다.</p>
        </header>

        {hasApiError ? (
          <section className="mt-8 rounded-2xl border border-yellow-400/30 bg-yellow-950/30 p-8">
            <h2 className="text-2xl font-black text-yellow-100">내 정보를 불러오지 못했습니다.</h2>
            <p className="mt-3 text-yellow-50">백엔드 서버와 Supabase 연결 상태를 확인해주세요.</p>
          </section>
        ) : (
          <>
            <section className="mt-8 grid gap-4 sm:grid-cols-4">
              <Metric label="플랜" value={subscription?.plan.toUpperCase() ?? "-"} />
              <Metric label="상태" value={subscription?.status ?? "-"} />
              <Metric label="오늘 남은 문제" value={`${subscription?.remainingToday ?? 0}/${subscription?.dailyQuestionLimit ?? 0}`} />
              <Metric label="연속 퀴즈" value={`${subscription?.streakDays ?? 0}일`} />
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
                  <h3 className="mt-4 text-xl font-black">아직 즐겨찾기한 문제가 없습니다.</h3>
                  <p className="mt-2 text-slate-300">문제 화면에서 별표를 누르면 이곳에 저장됩니다.</p>
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
