import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import AsyncSessionLocal  # noqa: E402


async def main() -> None:
    async with AsyncSessionLocal() as session:
        count = await session.scalar(
            text(
                """
                SELECT count(1)
                FROM questions q
                JOIN patterns p ON p.id = q.pattern_id
                WHERE p.slug = 'box-breakout'
                  AND q.timeframe = '1d'
                  AND q.is_synthetic = false
                """
            )
        )
        first_question = await session.execute(
            text(
                """
                SELECT q.id::text, q.source_symbol, q.correct_answer::text
                FROM questions q
                JOIN patterns p ON p.id = q.pattern_id
                WHERE p.slug = 'box-breakout'
                  AND q.timeframe = '1d'
                  AND q.is_synthetic = false
                ORDER BY q.created_at ASC
                LIMIT 1
                """
            )
        )
        row = first_question.first()

    print(f"real_daily_box_breakout_questions={count}")
    if row:
        print(f"first_question_id={row[0]}")
        print(f"first_question_source={row[1]}")
        print(f"first_question_answer={row[2]}")


if __name__ == "__main__":
    asyncio.run(main())
