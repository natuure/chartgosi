import Link from "next/link";

export default function WrongNotesPage() {
  return (
    <main className="min-h-screen bg-slate-950 px-4 py-8 text-white">
      <div className="mx-auto max-w-4xl">
        <h1 className="text-4xl font-black">오답 노트</h1>
        <div className="mt-8 rounded-2xl border border-white/10 bg-white/8 p-8">
          <p className="text-xl font-bold">아직 저장된 오답이 없습니다.</p>
          <p className="mt-2 text-slate-400">문제를 풀면 틀린 문제와 AI 해설이 여기에 쌓입니다.</p>
          <Link href="/play" className="mt-6 inline-block rounded-xl bg-cyan-500 px-5 py-3 font-black text-slate-950">
            오늘의 문제 풀기
          </Link>
        </div>
      </div>
    </main>
  );
}
