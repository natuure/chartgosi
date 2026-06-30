from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import QuestionResponse


DIFFICULTY_LABELS = {
    "easy": "초급",
    "medium": "중급",
    "hard": "고급",
}


async def get_today_question(session: AsyncSession) -> QuestionResponse | None:
    result = await session.execute(
        text(
            """
            SELECT
              q.id::text AS id,
              q.difficulty::text AS difficulty,
              q.market_regime::text AS market_regime,
              q.base_date::text AS base_date,
              q.chart_data,
              q.public_accuracy,
              p.id::text AS pattern_id,
              p.slug AS pattern_slug,
              p.name AS pattern_name
            FROM questions q
            JOIN patterns p ON p.id = q.pattern_id
            WHERE q.is_active = true
            ORDER BY q.created_at ASC
            LIMIT 1
            """
        )
    )
    row = result.mappings().first()
    if row is None:
        return None
    return row_to_question(row)


async def get_question(session: AsyncSession, question_id: str) -> QuestionResponse | None:
    result = await session.execute(
        text(
            """
            SELECT
              q.id::text AS id,
              q.difficulty::text AS difficulty,
              q.market_regime::text AS market_regime,
              q.base_date::text AS base_date,
              q.chart_data,
              q.public_accuracy,
              p.id::text AS pattern_id,
              p.slug AS pattern_slug,
              p.name AS pattern_name
            FROM questions q
            JOIN patterns p ON p.id = q.pattern_id
            WHERE q.id = CAST(:question_id AS uuid) AND q.is_active = true
            LIMIT 1
            """
        ),
        {"question_id": question_id},
    )
    row = result.mappings().first()
    if row is None:
        return None
    return row_to_question(row)


def row_to_question(row) -> QuestionResponse:
    difficulty = row["difficulty"]
    return QuestionResponse(
        id=row["id"],
        pattern={
            "id": row["pattern_id"],
            "slug": row["pattern_slug"],
            "name": row["pattern_name"],
            "question_count": 0,
        },
        difficulty=difficulty,
        difficulty_label=DIFFICULTY_LABELS.get(difficulty, difficulty),
        market_regime=row["market_regime"],
        base_date=row["base_date"],
        chart_data=row["chart_data"],
        public_accuracy=float(row["public_accuracy"]) if row["public_accuracy"] is not None else None,
    )
