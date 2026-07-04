import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { TrainingSessionClient } from "@/components/training-session-client";
import { getPatternSession } from "@/lib/api";
import { formatApiError } from "@/lib/api-errors";
import { getServerAccessToken } from "@/lib/server-auth";
import type { Question } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function TrainingPage({
  params,
}: {
  params: Promise<{ patternKey: string }>;
}) {
  const { patternKey } = await params;
  const accessToken = await getServerAccessToken();
  let questions: Question[] = [];
  let apiError: string | null = null;

  try {
    questions = await getPatternSession(patternKey, 10, accessToken);
  } catch (error) {
    apiError = formatApiError("연속 훈련", error);
  }

  if (apiError || questions.length === 0) {
    return (
      <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,#164e63_0%,#0f172a_42%,#020617_100%)] px-4 py-8 text-white">
        <div className="mx-auto max-w-3xl">
          <Link href="/patterns" className="inline-flex items-center gap-2 text-slate-300 transition hover:text-white">
            <ArrowLeft className="size-5" />
            패턴 목록으로
          </Link>
          <section className="mt-8 rounded-2xl border border-yellow-400/30 bg-yellow-950/30 p-8">
            <h1 className="text-2xl font-black text-yellow-100">연속 훈련을 시작할 수 없습니다.</h1>
            <p className="mt-3 text-yellow-50">{apiError ?? "이 패턴에 등록된 문제가 없습니다."}</p>
            <p className="mt-3 text-sm text-yellow-100">404라면 문제 seed를, 500이라면 Render 로그와 DB 연결 상태를 확인해주세요.</p>
            <Link href="/play" className="mt-6 inline-block rounded-xl bg-cyan-400 px-5 py-3 font-black text-slate-950">
              오늘의 문제 풀기
            </Link>
          </section>
        </div>
      </main>
    );
  }

  return <TrainingSessionClient patternKey={patternKey} questions={questions} />;
}
