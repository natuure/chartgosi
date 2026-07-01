"use client";

import { useEffect, useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { User } from "@supabase/supabase-js";
import { createSupabaseBrowserClient } from "@/lib/supabase";

export function AuthStatus() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    const supabase = createSupabaseBrowserClient();
    supabase.auth.getUser().then(({ data }) => setUser(data.user ?? null));
    const { data: subscription } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });
    return () => subscription.subscription.unsubscribe();
  }, []);

  function handleLogout() {
    startTransition(async () => {
      const supabase = createSupabaseBrowserClient();
      await supabase.auth.signOut();
      router.refresh();
    });
  }

  if (!user) {
    return (
      <Link className="flex items-center gap-2 border-l border-white/10 px-5 py-3 font-semibold" href="/login">
        로그인
      </Link>
    );
  }

  return (
    <button
      className="border-l border-white/10 px-5 py-3 text-left font-semibold"
      type="button"
      disabled={isPending}
      onClick={handleLogout}
    >
      로그아웃
    </button>
  );
}
