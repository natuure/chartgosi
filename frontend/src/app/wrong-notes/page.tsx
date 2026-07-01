import Link from "next/link";
import { ArrowLeft, BookOpenCheck, ChevronRight, ClipboardList, RotateCcw } from "lucide-react";
import { getWrongNotes } from "@/lib/api";
import type { AnswerDirection, WrongNoteItem } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function WrongNotesPage() {
  let wrongNotes: WrongNoteItem[] = [];
  let total = 0;
  let hasApiError = false;

  try {
    const response = await getWrongNotes();
    wrongNotes = response.items;
    total = response.total;
  } catch {
    hasApiError = true;
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,#1e1b4b_0%,#0f172a_42%,#020617_100%)] px-4 py-8 text-white">
      <div className="mx-auto max-w-5xl">
        <Link href="/" className="inline-flex items-center gap-2 text-slate-300 transition hover:text-white">
          <ArrowLeft className="size-5" />
          홈으로
        </Link>

        <header className="mt-6 flex flex-col gap-4 rounded-3xl border border-white/10 bg-white/8 p-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="flex items-center gap-2 text-cyan-300">
              <ClipboardList className="size-5" />
              복습 데이터
            </p>
            <h1 className="mt-2 text-4xl font-black">오답 노트</h1>
            <p className="mt-3 text-slate-300">틀린 문제를 다시 보고, 내 선택과 실제 정답을 비교해보세요.</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-slate-950/50 px-5 py-4">
            <p className="text-sm text-slate-400">저장된 오답</p>
            <p className="mt-1 text-3xl font-black text-red-300">{total}개</p>
          </div>
        </header>

        {hasApiError ? (
          <section className="mt-8 rounded-2xl border border-yellow-400/30 bg-yellow-950/30 p-8">
            <h2 className="text-2xl font-black text-yellow-100">오답노트를 불러오지 못했습니다.</h2>
            <p className="mt-3 text-yellow-50">백엔드 서버, DATABASE_URL, Supabase 연결 상태를 확인해주세요.</p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row">
              <Link href="/" className="rounded-xl border border-white/10 px-5 py-3 text-center font-bold">
                홈으로 이동
              </Link>
              <Link href="/play" className="rounded-xl bg-cyan-400 px-5 py-3 text-center font-black text-slate-950">
                문제 풀기
              </Link>
            </div>
          </section>
        ) : wrongNotes.length === 0 ? (
          <section className="mt-8 rounded-2xl border border-white/10 bg-white/8 p-8">
            <BookOpenCheck className="size-12 text-cyan-300" />
            <h2 className="mt-5 text-2xl font-black">아직 저장된 오답이 없습니다.</h2>
            <p className="mt-3 text-slate-300">문제를 풀다가 틀리면 이곳에 자동으로 저장됩니다.</p>
            <Link href="/play" className="mt-6 inline-flex items-center gap-2 rounded-xl bg-cyan-400 px-5 py-3 font-black text-slate-950">
              오늘의 문제 풀기
              <ChevronRight className="size-5" />
            </Link>
          </section>
        ) : (
          <section className="mt-8 grid gap-4">
            {wrongNotes.map((note) => (
              <article
                key={note.answerId}
                className="rounded-2xl border border-white/10 bg-white/8 p-6 transition hover:border-cyan-300/50 hover:bg-white/10"
              >
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p className="text-sm font-bold text-cyan-300">{note.pattern.name} · {note.difficultyLabel}</p>
                    <h2 className="mt-2 text-2xl font-black">기준일 {note.baseDate} 문제 복습</h2>
                    <p className="mt-3 line-clamp-2 text-slate-300">
                      {note.aiExplanation ?? "등록된 AI 해설이 없습니다."}
                    </p>
                  </div>
                  <div className="flex shrink-0 gap-3">
                    <AnswerBadge label="내 선택" answer={note.selectedAnswer} tone="red" />
                    <AnswerBadge label="정답" answer={note.correctAnswer} tone="green" />
                  </div>
                </div>
                <div className="mt-5 flex flex-col gap-3 border-t border-white/10 pt-4 text-sm text-slate-400 sm:flex-row sm:items-center sm:justify-between">
                  <span>{formatDateTime(note.createdAt)} 제출</span>
                  <div className="flex flex-col gap-2 sm:flex-row">
                    <Link
                      href={`/result/${note.answerId}`}
                      className="inline-flex items-center justify-center gap-1 rounded-xl border border-white/10 px-4 py-2 font-bold text-cyan-300 transition hover:border-cyan-300/50"
                    >
                      결과 다시 보기
                      <ChevronRight className="size-4" />
                    </Link>
                    <Link
                      href={`/play?question_id=${encodeURIComponent(note.questionId)}&retry=1`}
                      className="inline-flex items-center justify-center gap-1 rounded-xl bg-cyan-400 px-4 py-2 font-black text-slate-950"
                    >
                      <RotateCcw className="size-4" />
                      다시 풀기
                    </Link>
                  </div>
                </div>
              </article>
            ))}
          </section>
        )}
      </div>
    </main>
  );
}

function AnswerBadge({
  label,
  answer,
  tone,
}: {
  label: string;
  answer: AnswerDirection;
  tone: "green" | "red";
}) {
  const colorClass = tone === "green" ? "text-emerald-300" : "text-red-300";

  return (
    <div className="min-w-24 rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-center">
      <p className="text-xs text-slate-400">{label}</p>
      <p className={`mt-1 font-black ${colorClass}`}>{answerLabel(answer)}</p>
    </div>
  );
}

function answerLabel(answer: AnswerDirection) {
  return {
    up: "상승",
    sideways: "횡보",
    down: "하락",
  }[answer];
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
