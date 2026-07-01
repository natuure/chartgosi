"use client";

import { useEffect } from "react";
import { ACCESS_TOKEN_COOKIE } from "@/lib/auth-constants";
import { createSupabaseBrowserClient } from "@/lib/supabase";

const COOKIE_MAX_AGE_SECONDS = 60 * 60;

export function AuthSessionSync() {
  useEffect(() => {
    let isMounted = true;
    const supabase = createSupabaseBrowserClient();

    function syncAccessToken(accessToken?: string | null) {
      if (!isMounted) {
        return;
      }
      const secureCookie = window.location.protocol === "https:" ? "; Secure" : "";
      if (accessToken) {
        document.cookie = `${ACCESS_TOKEN_COOKIE}=${accessToken}; Path=/; Max-Age=${COOKIE_MAX_AGE_SECONDS}; SameSite=Lax${secureCookie}`;
      } else {
        document.cookie = `${ACCESS_TOKEN_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax${secureCookie}`;
      }
    }

    supabase.auth.getSession().then(({ data }) => {
      syncAccessToken(data.session?.access_token);
    });

    const { data: subscription } = supabase.auth.onAuthStateChange((_event, session) => {
      syncAccessToken(session?.access_token);
    });

    return () => {
      isMounted = false;
      subscription.subscription.unsubscribe();
    };
  }, []);

  return null;
}
