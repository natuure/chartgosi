from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import QuestionListItem, QuestionResponse


DIFFICULTY_LABELS = {
    "easy": "초급",
    "medium": "중급",
    "hard": "고급",
}


async def get_today_question(
    session: AsyncSession,
    pattern_slug: str | None = None,
    user_id: str | None = None,
) -> QuestionResponse | None:
    result = await session.execute(
        text(
            """
            SELECT
              q.id::text AS id,
              q.difficulty::text AS difficulty,
              q.market_regime::text AS market_regime,
              q.timeframe,
              q.base_date::text AS base_date,
              q.chart_data,
              q.pattern_evidence,
              q.rule_score,
              q.public_accuracy,
              EXISTS (
                SELECT 1
                FROM favorite_questions fq
                WHERE fq.user_id = CAST(:user_id AS uuid) AND fq.question_id = q.id
              ) AS is_favorited,
              p.id::text AS pattern_id,
              p.slug AS pattern_slug,
              p.name AS pattern_name,
              p.description AS pattern_description,
              p.definition AS pattern_definition
            FROM questions q
            JOIN patterns p ON p.id = q.pattern_id
            WHERE q.is_active = true
              AND (CAST(:pattern_slug AS text) IS NULL OR p.slug = CAST(:pattern_slug AS text))
            ORDER BY
              CASE WHEN p.slug = 'cup-and-handle' AND q.timeframe = '1w' THEN 0 ELSE 1 END,
              q.created_at ASC
            LIMIT 1
            """
        ),
        {"pattern_slug": pattern_slug, "user_id": user_id},
    )
    row = result.mappings().first()
    if row is None:
        return None
    return row_to_question(row)


async def get_question(session: AsyncSession, question_id: str, user_id: str | None = None) -> QuestionResponse | None:
    result = await session.execute(
        text(
            """
            SELECT
              q.id::text AS id,
              q.difficulty::text AS difficulty,
              q.market_regime::text AS market_regime,
              q.timeframe,
              q.base_date::text AS base_date,
              q.chart_data,
              q.pattern_evidence,
              q.rule_score,
              q.public_accuracy,
              EXISTS (
                SELECT 1
                FROM favorite_questions fq
                WHERE fq.user_id = CAST(:user_id AS uuid) AND fq.question_id = q.id
              ) AS is_favorited,
              p.id::text AS pattern_id,
              p.slug AS pattern_slug,
              p.name AS pattern_name,
              p.description AS pattern_description,
              p.definition AS pattern_definition
            FROM questions q
            JOIN patterns p ON p.id = q.pattern_id
            WHERE q.id = CAST(:question_id AS uuid) AND q.is_active = true
            LIMIT 1
            """
        ),
        {"question_id": question_id, "user_id": user_id},
    )
    row = result.mappings().first()
    if row is None:
        return None
    return row_to_question(row)


async def list_pattern_questions(
    session: AsyncSession,
    pattern_key: str,
    user_id: str | None = None,
) -> list[QuestionListItem]:
    result = await session.execute(
        text(
            """
            SELECT
              q.id::text AS id,
              q.difficulty::text AS difficulty,
              q.market_regime::text AS market_regime,
              q.timeframe,
              q.base_date::text AS base_date,
              q.public_accuracy,
              q.rule_score,
              q.total_answers,
              EXISTS (
                SELECT 1
                FROM favorite_questions fq
                WHERE fq.user_id = CAST(:user_id AS uuid) AND fq.question_id = q.id
              ) AS is_favorited,
              p.id::text AS pattern_id,
              p.slug AS pattern_slug,
              p.name AS pattern_name,
              p.description AS pattern_description,
              p.definition AS pattern_definition
            FROM questions q
            JOIN patterns p ON p.id = q.pattern_id
            WHERE
              q.is_active = true
              AND p.is_active = true
              AND (p.slug = :pattern_key OR p.id::text = :pattern_key)
            ORDER BY
              CASE WHEN p.slug = 'cup-and-handle' AND q.timeframe = '1w' THEN 0 ELSE 1 END,
              q.created_at ASC
            """
        ),
        {"pattern_key": pattern_key, "user_id": user_id},
    )
    return [row_to_question_list_item(row) for row in result.mappings().all()]


async def list_pattern_session_questions(
    session: AsyncSession,
    pattern_key: str,
    limit: int,
    user_id: str | None = None,
) -> list[QuestionResponse]:
    result = await session.execute(
        text(
            """
            SELECT
              q.id::text AS id,
              q.difficulty::text AS difficulty,
              q.market_regime::text AS market_regime,
              q.timeframe,
              q.base_date::text AS base_date,
              q.chart_data,
              q.pattern_evidence,
              q.rule_score,
              q.public_accuracy,
              EXISTS (
                SELECT 1
                FROM favorite_questions fq
                WHERE fq.user_id = CAST(:user_id AS uuid) AND fq.question_id = q.id
              ) AS is_favorited,
              p.id::text AS pattern_id,
              p.slug AS pattern_slug,
              p.name AS pattern_name,
              p.description AS pattern_description,
              p.definition AS pattern_definition
            FROM questions q
            JOIN patterns p ON p.id = q.pattern_id
            WHERE
              q.is_active = true
              AND p.is_active = true
              AND (p.slug = :pattern_key OR p.id::text = :pattern_key)
            ORDER BY
              CASE WHEN p.slug = 'cup-and-handle' AND q.timeframe = '1w' THEN 0 ELSE 1 END,
              q.created_at ASC
            LIMIT :limit
            """
        ),
        {"pattern_key": pattern_key, "limit": limit, "user_id": user_id},
    )
    return [row_to_question(row) for row in result.mappings().all()]


def row_to_question(row) -> QuestionResponse:
    difficulty = row["difficulty"]
    return QuestionResponse(
        id=row["id"],
        pattern={
            "id": row["pattern_id"],
            "slug": row["pattern_slug"],
            "name": row["pattern_name"],
            "question_count": 0,
            "description": row["pattern_description"],
            "definition": row["pattern_definition"],
        },
        difficulty=difficulty,
        difficulty_label=DIFFICULTY_LABELS.get(difficulty, difficulty),
        market_regime=row["market_regime"],
        timeframe=row["timeframe"],
        base_date=row["base_date"],
        chart_data=row["chart_data"],
        public_accuracy=float(row["public_accuracy"]) if row["public_accuracy"] is not None else None,
        pattern_score=float(row["rule_score"]) if row["rule_score"] is not None else None,
        is_favorited=row["is_favorited"],
        pattern_evidence=row["pattern_evidence"] or [],
    )


def row_to_question_list_item(row) -> QuestionListItem:
    difficulty = row["difficulty"]
    return QuestionListItem(
        id=row["id"],
        pattern={
            "id": row["pattern_id"],
            "slug": row["pattern_slug"],
            "name": row["pattern_name"],
            "question_count": 0,
            "description": row["pattern_description"],
            "definition": row["pattern_definition"],
        },
        difficulty=difficulty,
        difficulty_label=DIFFICULTY_LABELS.get(difficulty, difficulty),
        market_regime=row["market_regime"],
        timeframe=row["timeframe"],
        base_date=row["base_date"],
        public_accuracy=float(row["public_accuracy"]) if row["public_accuracy"] is not None else None,
        pattern_score=float(row["rule_score"]) if row["rule_score"] is not None else None,
        total_answers=row["total_answers"],
        is_favorited=row["is_favorited"],
    )
