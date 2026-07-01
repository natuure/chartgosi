"use client";

import { useEffect } from "react";
import { markAnswerExplanationViewed } from "@/lib/api";

export function ExplanationViewTracker({
  answerId,
  enabled,
}: {
  answerId: string;
  enabled: boolean;
}) {
  useEffect(() => {
    if (!enabled) {
      return;
    }

    void markAnswerExplanationViewed(answerId).catch(() => {
      // Viewing the explanation should never block the result screen.
    });
  }, [answerId, enabled]);

  return null;
}
