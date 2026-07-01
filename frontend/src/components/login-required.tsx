import Link from "next/link";

export function LoginRequired({ nextPath, title = "로그인이 필요합니다." }: { nextPath: string; title?: string }) {
  return (
    <section className="mt-8 rounded-2xl border border-cyan-300/30 bg-cyan-950/30 p-8">
      <h2 className="text-2xl font-black text-cyan-100">{title}</h2>
      <p className="mt-3 text-cyan-50">답안, 오답노트, 통계, AI 리포트는 내 계정에 저장됩니다.</p>
      <Link
        href={`/login?next=${encodeURIComponent(nextPath)}`}
        className="mt-6 inline-block rounded-xl bg-cyan-400 px-5 py-3 font-black text-slate-950"
      >
        로그인하기
      </Link>
    </section>
  );
}
