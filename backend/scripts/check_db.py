import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import AsyncSessionLocal  # noqa: E402
from app.repositories.patterns import list_patterns  # noqa: E402
from app.repositories.questions import get_today_question  # noqa: E402


async def main() -> None:
    async with AsyncSessionLocal() as session:
        patterns = await list_patterns(session)
        question = await get_today_question(session)

    print(f"patterns={len(patterns)}")
    print(f"question_id={question.id if question else None}")


if __name__ == "__main__":
    asyncio.run(main())
