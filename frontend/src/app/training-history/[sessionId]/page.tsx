import Link from "next/link";
import { ArrowLeft, CheckCircle2, RotateCcw, XCircle } from "lucide-react";
import { LoginRequired } from "@/components/login-required";
import { getTrainingSessionDetail } from "@/lib/api";
import { formatApiError } from "@/lib/api-errors";
import { getServerAccessToken } from "@/lib/server-auth";
import type { AnswerResult, TrainingSessionDetail } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function TrainingHistoryDetailPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  const accessToken = await getServerAccessToken();
  let detail: TrainingSessionDetail | null = null;
  let apiError: string | null = null;

  if (!accessToken) {
    return <PageShell><LoginRequired nextPath={`/training-history/${sessionId}`} title="훈련 기록 상세는 로그인이 필요합니다" /></PageShell>;
  }

  try {
    detail = await getTrainingSessionDetail(sessionId, accessToken);
  } catch (error) {
    apiError = formatApiError("훈련 세션", error);
  }

  if (apiError || !detail) {
    return (
      <PageShell>
        <section className="mt-8 rounded-2xl border border-yellow-400/30 bg-yellow-950/30 p-8">
          <h1 className="text-2xl font-black text-yellow-100">훈련 세션을 불러오지 못했습니다</h1>
          <p className="mt-3 text-yellow-50">{apiError ?? "세션이 없거나 현재 계정의 기록이 아닐 수 있습니다."}</p>
          <p className="mt-3 text-sm text-yellow-100">404이면 현재 계정의 세션이 아니거나 없는 세션이고, 401이면 로그인 세션을 다시 확인해야 합니다.</p>
          <Link href="/training-history" className="mt-6 inline-block rounded-xl bg-cyan-400 px-5 py-3 font-black text-slate-950">
            기록 목록으로
          </Link>
        </section>
      </PageShell>
    );
  }

  const accuracy = Math.round(detail.session.accuracy * 100);

  return (
    <PageShell>
      <header className="mt-6 rounded-3xl border border-white/10 bg-white/8 p-6">
        <p className="text-cyan-300">훈련 세션 상세</p>
        <h1 className="mt-2 text-4xl font-black">{detail.session.pattern.name}</h1>
        <p className="mt-3 text-slate-300">
          {formatDateTime(detail.session.startedAt)}부터 {detail.session.solvedCount}문제를 풀었습니다.
        </p>
      </header>

      <section className="mt-8 grid gap-4 sm:grid-cols-3">
        <Metric label="총 문제" value={`${detail.session.solvedCount}문제`} />
        <Metric label="정답" value={`${detail.session.correctCount}문제`} />
        <Metric label="정답률" value={`${accuracy}%`} />
      </section>

      <section className="mt-8 overflow-hidden rounded-2xl border border-white/10 bg-white/8">
        {detail.answers.map((answer, index) => (
          <div key={answer.answerId} className="grid gap-4 border-b border-white/10 p-5 last:border-b-0 md:grid-cols-[80px_1fr_160px_160px_120px]">
            <strong className="text-cyan-300">#{index + 1}</strong>
            <div>
              <p className="font-black">{answer.pattern.name}</p>
              <p className="mt-1 text-sm text-slate-400">
                내 선택: {answerLabel(answer.selectedAnswer)} / 정답: {answerLabel(answer.correctAnswer)}
              </p>
            </div>
            <StatusBadge isCorrect={answer.isCorrect} />
            <Link href={`/result/${answer.answerId}`} className="rounded-xl border border-white/10 px-4 py-3 text-center font-bold text-slate-200 transition hover:border-cyan-300/60">
              해설 보기
            </Link>
            <Link href={`/play?question_id=${encodeURIComponent(answer.questionId)}&retry=1`} className="rounded-xl bg-slate-800 px-4 py-3 text-center font-bold text-slate-100 transition hover:bg-slate-700">
              재도전
            </Link>
          </div>
        ))}
      </section>

      <div className="mt-8 grid gap-3 sm:grid-cols-2">
        <Link
          href={`/training/${encodeURIComponent(detail.session.pattern.slug)}`}
          className="inline-flex items-center justify-center gap-2 rounded-2xl bg-cyan-400 px-5 py-4 font-black text-slate-950 transition hover:bg-cyan-300"
        >
          <RotateCcw className="size-5" />
          같은 패턴 다시 훈련
        </Link>
        <Link href="/training-history" className="rounded-2xl border border-white/10 px-5 py-4 text-center font-black text-slate-100 transition hover:border-cyan-300/60">
          전체 기록 보기
        </Link>
      </div>
    </PageShell>
  );
}

function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,#172554_0%,#0f172a_42%,#020617_100%)] px-4 py-8 text-white">
      <div className="mx-auto max-w-5xl">
        <Link href="/training-history" className="inline-flex items-center gap-2 text-slate-300 transition hover:text-white">
          <ArrowLeft className="size-5" />
          훈련 기록으로
        </Link>
        {children}
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/8 p-6">
      <p className="text-sm text-slate-400">{label}</p>
      <p className="mt-2 text-3xl font-black text-cyan-300">{value}</p>
    </div>
  );
}

function StatusBadge({ isCorrect }: { isCorrect: boolean }) {
  return (
    <span className={isCorrect ? "inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-400/15 px-4 py-3 font-black text-emerald-200" : "inline-flex items-center justify-center gap-2 rounded-xl bg-red-400/15 px-4 py-3 font-black text-red-200"}>
      {isCorrect ? <CheckCircle2 className="size-5" /> : <XCircle className="size-5" />}
      {isCorrect ? "정답" : "오답"}
    </span>
  );
}

function answerLabel(answer: AnswerResult["selectedAnswer"]) {
  if (answer === "up") {
    return "상승";
  }
  if (answer === "sideways") {
    return "횡보";
  }
  return "하락";
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
