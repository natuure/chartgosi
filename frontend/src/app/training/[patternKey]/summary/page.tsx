import Link from "next/link";
import { ArrowLeft, CheckCircle2, RotateCcw, XCircle } from "lucide-react";
import { LoginRequired } from "@/components/login-required";
import { getAnswerResult } from "@/lib/api";
import { getServerAccessToken } from "@/lib/server-auth";
import type { AnswerResult } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function TrainingSummaryPage({
  params,
  searchParams,
}: {
  params: Promise<{ patternKey: string }>;
  searchParams: Promise<{ answers?: string }>;
}) {
  const { patternKey } = await params;
  const { answers } = await searchParams;
  const answerIds = parseAnswerIds(answers);
  const accessToken = await getServerAccessToken();
  let results: AnswerResult[] = [];
  let hasApiError = false;

  if (!accessToken) {
    return (
      <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,#164e63_0%,#0f172a_42%,#020617_100%)] px-4 py-8 text-white">
        <div className="mx-auto max-w-4xl">
          <LoginRequired nextPath={`/training/${patternKey}/summary${answers ? `?answers=${encodeURIComponent(answers)}` : ""}`} title="훈련 결과 확인에는 로그인이 필요합니다." />
        </div>
      </main>
    );
  }

  try {
    results = await Promise.all(answerIds.map((answerId) => getAnswerResult(answerId, accessToken)));
  } catch {
    hasApiError = true;
  }

  const correctCount = results.filter((result) => result.isCorrect).length;
  const accuracy = results.length > 0 ? Math.round((correctCount / results.length) * 100) : 0;
  const patternName = results[0]?.pattern.name ?? "패턴";

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,#164e63_0%,#0f172a_42%,#020617_100%)] px-4 py-8 text-white">
      <div className="mx-auto max-w-5xl">
        <Link href="/patterns" className="inline-flex items-center gap-2 text-slate-300 transition hover:text-white">
          <ArrowLeft className="size-5" />
          패턴 목록으로
        </Link>

        <header className="mt-6 rounded-3xl border border-white/10 bg-white/8 p-6">
          <p className="text-cyan-300">연속 훈련 결과</p>
          <h1 className="mt-2 text-4xl font-black">{patternName}</h1>
          <p className="mt-3 text-slate-300">이번 세션에서 제출한 답안을 기준으로 결과를 요약했습니다.</p>
        </header>

        {hasApiError || answerIds.length === 0 ? (
          <section className="mt-8 rounded-2xl border border-yellow-400/30 bg-yellow-950/30 p-8">
            <h2 className="text-2xl font-black text-yellow-100">세션 결과를 불러오지 못했습니다.</h2>
            <p className="mt-3 text-yellow-50">답안 ID 목록 또는 로그인 상태를 확인해주세요.</p>
            <Link href={`/training/${encodeURIComponent(patternKey)}`} className="mt-6 inline-block rounded-xl bg-cyan-400 px-5 py-3 font-black text-slate-950">
              다시 훈련하기
            </Link>
          </section>
        ) : (
          <>
            <section className="mt-8 grid gap-4 sm:grid-cols-3">
              <Metric label="푼 문제" value={`${results.length}문제`} />
              <Metric label="정답" value={`${correctCount}문제`} />
              <Metric label="정답률" value={`${accuracy}%`} />
            </section>

            <section className="mt-8 overflow-hidden rounded-2xl border border-white/10 bg-white/8">
              {results.map((result, index) => (
                <div key={result.answerId} className="grid gap-4 border-b border-white/10 p-5 last:border-b-0 md:grid-cols-[80px_1fr_160px_160px_120px]">
                  <strong className="text-cyan-300">#{index + 1}</strong>
                  <div>
                    <p className="font-black">{result.pattern.name}</p>
                    <p className="mt-1 text-sm text-slate-400">
                      내 선택: {answerLabel(result.selectedAnswer)} / 정답: {answerLabel(result.correctAnswer)}
                    </p>
                  </div>
                  <StatusBadge isCorrect={result.isCorrect} />
                  <Link href={`/result/${result.answerId}`} className="rounded-xl border border-white/10 px-4 py-3 text-center font-bold text-slate-200 transition hover:border-cyan-300/60">
                    해설 보기
                  </Link>
                  <Link href={`/play?question_id=${encodeURIComponent(result.questionId)}&retry=1`} className="rounded-xl bg-slate-800 px-4 py-3 text-center font-bold text-slate-100 transition hover:bg-slate-700">
                    재도전
                  </Link>
                </div>
              ))}
            </section>

            <div className="mt-8 grid gap-3 sm:grid-cols-2">
              <Link
                href={`/training/${encodeURIComponent(patternKey)}`}
                className="inline-flex items-center justify-center gap-2 rounded-2xl bg-cyan-400 px-5 py-4 font-black text-slate-950 transition hover:bg-cyan-300"
              >
                <RotateCcw className="size-5" />
                같은 패턴 다시 훈련
              </Link>
              <Link href="/wrong-notes" className="rounded-2xl border border-white/10 px-5 py-4 text-center font-black text-slate-100 transition hover:border-cyan-300/60">
                오답노트 보기
              </Link>
            </div>
          </>
        )}
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

function parseAnswerIds(value?: string): string[] {
  if (!value) {
    return [];
  }
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
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
