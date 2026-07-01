"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Sparkles } from "lucide-react";
import { generateAiReport } from "@/lib/api";
import { getBrowserAccessToken } from "@/lib/browser-auth";

export function AiReportGenerateButton({ label = "AI 리포트 생성하기" }: { label?: string }) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function handleClick() {
    setError(null);
    startTransition(async () => {
      try {
        const accessToken = await getBrowserAccessToken();
        if (!accessToken) {
          router.push(`/login?next=${encodeURIComponent(window.location.pathname + window.location.search)}`);
          return;
        }
        await generateAiReport(accessToken);
        router.refresh();
      } catch {
        setError("AI 리포트를 생성하지 못했습니다.");
      }
    });
  }

  return (
    <div>
      <button
        className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-fuchsia-500 to-cyan-400 px-5 py-3 font-black text-white transition hover:brightness-110 disabled:opacity-60"
        type="button"
        disabled={isPending}
        onClick={handleClick}
      >
        <Sparkles className="size-5" />
        {isPending ? "생성 중..." : label}
      </button>
      {error ? <p className="mt-2 text-sm text-red-300">{error}</p> : null}
    </div>
  );
}
