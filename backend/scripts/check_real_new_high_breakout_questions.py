import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import AsyncSessionLocal


async def main() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT
                  COUNT(*) AS question_count,
                  MIN(q.id::text) AS first_question_id
                FROM questions q
                JOIN patterns p ON p.id = q.pattern_id
                WHERE p.slug = 'new-high-breakout'
                  AND q.timeframe = '1d'
                  AND q.is_synthetic = false
                  AND q.is_active = true
                """
            )
        )
        row = result.mappings().one()
        print(f"real_daily_new_high_breakout_questions={row['question_count']}")
        print(f"first_question_id={row['first_question_id']}")

        sample_result = await session.execute(
            text(
                """
                SELECT
                  q.symbol,
                  q.source_symbol,
                  q.correct_answer::text AS correct_answer,
                  q.rule_score,
                  q.base_date::text AS base_date
                FROM questions q
                JOIN patterns p ON p.id = q.pattern_id
                WHERE p.slug = 'new-high-breakout'
                  AND q.timeframe = '1d'
                  AND q.is_synthetic = false
                  AND q.is_active = true
                ORDER BY q.id
                LIMIT 3
                """
            )
        )
        for sample in sample_result.mappings().all():
            print(
                "sample="
                f"{sample['symbol']} "
                f"{sample['source_symbol']} "
                f"{sample['correct_answer']} "
                f"score={sample['rule_score']} "
                f"base_date={sample['base_date']}"
            )


if __name__ == "__main__":
    asyncio.run(main())
