import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { LoginClient } from "@/components/login-client";

export const dynamic = "force-dynamic";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const { next } = await searchParams;
  const nextPath = next && next.startsWith("/") ? next : "/";

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,#172554_0%,#0f172a_42%,#020617_100%)] px-4 py-8 text-white">
      <div className="mx-auto max-w-md">
        <Link href="/" className="inline-flex items-center gap-2 text-slate-300 transition hover:text-white">
          <ArrowLeft className="size-5" />
          홈으로
        </Link>

        <header className="mt-8">
          <p className="text-cyan-300">차트고시 계정</p>
          <h1 className="mt-2 text-4xl font-black">로그인</h1>
          <p className="mt-3 text-slate-300">답안, 오답노트, 통계, AI 리포트를 내 계정에 저장합니다.</p>
        </header>

        <LoginClient nextPath={nextPath} />
      </div>
    </main>
  );
}
