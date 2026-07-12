import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import AsyncSessionLocal


PATTERN_SLUGS = (
    "pullback",
    "triangle",
    "flag",
    "flat-base",
    "bullish-engulfing",
    "early-stage2",
    "volume-spike",
)


async def main() -> None:
    async with AsyncSessionLocal() as session:
        for slug in PATTERN_SLUGS:
            timeframe = "1w" if slug in {"triangle", "flag", "flat-base", "early-stage2"} else "1d"
            result = await session.execute(
                text(
                    """
                    SELECT
                      COUNT(*) AS question_count,
                      COUNT(*) FILTER (WHERE q.correct_answer = 'up') AS up_count,
                      COUNT(*) FILTER (WHERE q.correct_answer = 'sideways') AS sideways_count,
                      COUNT(*) FILTER (WHERE q.correct_answer = 'down') AS down_count,
                      MIN(q.id::text) AS first_question_id
                    FROM questions q
                    JOIN patterns p ON p.id = q.pattern_id
                    WHERE p.slug = :slug
                      AND q.timeframe = :timeframe
                      AND q.is_synthetic = false
                      AND q.is_active = true
                    """
                ),
                {"slug": slug, "timeframe": timeframe},
            )
            row = result.mappings().one()
            print(
                f"{slug}({timeframe}): total={row['question_count']} "
                f"up={row['up_count']} sideways={row['sideways_count']} down={row['down_count']} "
                f"first={row['first_question_id']}"
            )


if __name__ == "__main__":
    asyncio.run(main())
