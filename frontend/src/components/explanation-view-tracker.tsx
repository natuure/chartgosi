"use client";

import { useEffect } from "react";
import { markAnswerExplanationViewed } from "@/lib/api";

export function ExplanationViewTracker({
  answerId,
  enabled,
  accessToken,
}: {
  answerId: string;
  enabled: boolean;
  accessToken: string;
}) {
  useEffect(() => {
    if (!enabled) {
      return;
    }

    void markAnswerExplanationViewed(answerId, accessToken).catch(() => {
      // Viewing the explanation should never block the result screen.
    });
  }, [accessToken, answerId, enabled]);

  return null;
}
