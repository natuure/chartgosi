"use client";

import { FormEvent, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { createSupabaseBrowserClient } from "@/lib/supabase";

export function LoginClient({ nextPath }: { nextPath: string }) {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    setError(null);

    startTransition(async () => {
      try {
        const supabase = createSupabaseBrowserClient();
        const response =
          mode === "login"
            ? await supabase.auth.signInWithPassword({ email, password })
            : await supabase.auth.signUp({ email, password });

        if (response.error) {
          setError(response.error.message);
          return;
        }

        if (mode === "signup" && !response.data.session) {
          setMessage("가입 확인 메일을 보냈습니다. 메일 인증 후 로그인해주세요.");
          return;
        }

        router.replace(nextPath);
        router.refresh();
      } catch {
        setError("Supabase에 연결하지 못했습니다. Vercel의 NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY 값을 확인하고 다시 배포해주세요.");
      }
    });
  }

  return (
    <section className="mt-8 rounded-3xl border border-white/10 bg-white/8 p-6">
      <div className="mb-6 grid grid-cols-2 rounded-2xl bg-slate-950/60 p-1">
        <button
          className={mode === "login" ? "rounded-xl bg-cyan-400 py-3 font-black text-slate-950" : "py-3 font-bold text-slate-300"}
          type="button"
          onClick={() => setMode("login")}
        >
          로그인
        </button>
        <button
          className={mode === "signup" ? "rounded-xl bg-cyan-400 py-3 font-black text-slate-950" : "py-3 font-bold text-slate-300"}
          type="button"
          onClick={() => setMode("signup")}
        >
          회원가입
        </button>
      </div>

      <form className="space-y-4" onSubmit={handleSubmit}>
        <label className="block">
          <span className="text-sm font-bold text-slate-300">이메일</span>
          <input
            className="mt-2 w-full rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white outline-none transition focus:border-cyan-300"
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>
        <label className="block">
          <span className="text-sm font-bold text-slate-300">비밀번호</span>
          <input
            className="mt-2 w-full rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white outline-none transition focus:border-cyan-300"
            type="password"
            required
            minLength={6}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>

        <button
          className="w-full rounded-2xl bg-gradient-to-r from-purple-600 to-sky-500 py-4 font-black text-white transition hover:brightness-110 disabled:opacity-60"
          type="submit"
          disabled={isPending}
        >
          {isPending ? "처리 중..." : mode === "login" ? "로그인하기" : "가입하기"}
        </button>
      </form>

      {message ? <p className="mt-4 rounded-xl border border-cyan-300/30 bg-cyan-950/30 p-3 text-sm text-cyan-100">{message}</p> : null}
      {error ? <p className="mt-4 rounded-xl border border-red-300/30 bg-red-950/30 p-3 text-sm text-red-100">{error}</p> : null}
    </section>
  );
}
