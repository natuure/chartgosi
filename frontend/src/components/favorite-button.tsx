"use client";

import { useState, useTransition } from "react";
import { Star } from "lucide-react";
import { addFavoriteQuestion, removeFavoriteQuestion } from "@/lib/api";

export function FavoriteButton({
  questionId,
  initialIsFavorited,
}: {
  questionId: string;
  initialIsFavorited: boolean;
}) {
  const [isFavorited, setIsFavorited] = useState(initialIsFavorited);
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function handleToggle() {
    setError(null);
    startTransition(async () => {
      try {
        const result = isFavorited
          ? await removeFavoriteQuestion(questionId)
          : await addFavoriteQuestion(questionId);
        setIsFavorited(result.isFavorited);
      } catch {
        setError("즐겨찾기 변경에 실패했습니다.");
      }
    });
  }

  return (
    <div className="flex flex-col items-end gap-2">
      <button
        className="flex items-center gap-2 text-slate-300 transition hover:text-yellow-200 disabled:opacity-60"
        type="button"
        disabled={isPending}
        onClick={handleToggle}
      >
        <Star className={`size-6 ${isFavorited ? "fill-yellow-300 text-yellow-300" : ""}`} />
        {isFavorited ? "즐겨찾기됨" : "즐겨찾기"}
      </button>
      {error ? <p className="text-xs text-red-300">{error}</p> : null}
    </div>
  );
}
