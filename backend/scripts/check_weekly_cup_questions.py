import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import AsyncSessionLocal  # noqa: E402


async def main() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT COUNT(*)::int
                FROM questions q
                JOIN patterns p ON p.id = q.pattern_id
                WHERE p.slug = 'cup-and-handle'
                  AND q.timeframe = '1w'
                  AND q.is_active = true
                """
            )
        )
        count = result.scalar_one()

    print(f"weekly_cup_handle_questions={count}")


if __name__ == "__main__":
    asyncio.run(main())
