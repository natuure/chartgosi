"use client";

import { createSupabaseBrowserClient } from "@/lib/supabase";

export async function getBrowserAccessToken(): Promise<string | null> {
  const supabase = createSupabaseBrowserClient();
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}
