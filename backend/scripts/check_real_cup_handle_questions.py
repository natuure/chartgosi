import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import AsyncSessionLocal  # noqa: E402
from app.repositories.questions import get_today_question  # noqa: E402


async def main() -> None:
    async with AsyncSessionLocal() as session:
        count_result = await session.execute(
            text(
                """
                SELECT COUNT(*)::int
                FROM questions q
                JOIN patterns p ON p.id = q.pattern_id
                WHERE p.slug = 'cup-and-handle'
                  AND q.timeframe = '1w'
                  AND q.is_synthetic = false
                  AND q.rule_score >= 80
                  AND q.is_active = true
                """
            )
        )
        count = count_result.scalar_one()
        question = await get_today_question(session, pattern_slug="cup-and-handle")

    print(f"real_weekly_cup_handle_questions={count}")
    print(f"first_question_id={question.id if question else None}")
    print(f"first_question_source={question.source_symbol if question else None}")
    print(f"first_question_synthetic={question.is_synthetic if question else None}")


if __name__ == "__main__":
    asyncio.run(main())
