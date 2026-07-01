from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.questions import DIFFICULTY_LABELS
from app.schemas import FavoriteQuestionItem, FavoritesResponse, FavoriteToggleResponse


async def list_favorites(session: AsyncSession, user_id: str) -> FavoritesResponse:
    result = await session.execute(
        text(
            """
            SELECT
              fq.id::text AS favorite_id,
              fq.created_at::text AS created_at,
              q.id::text AS question_id,
              q.difficulty::text AS difficulty,
              q.market_regime::text AS market_regime,
              q.base_date::text AS base_date,
              q.public_accuracy,
              q.total_answers,
              p.id::text AS pattern_id,
              p.slug AS pattern_slug,
              p.name AS pattern_name
            FROM favorite_questions fq
            JOIN questions q ON q.id = fq.question_id
            JOIN patterns p ON p.id = q.pattern_id
            WHERE fq.user_id = CAST(:user_id AS uuid)
            ORDER BY fq.created_at DESC
            """
        ),
        {"user_id": user_id},
    )
    items = [row_to_favorite_item(row) for row in result.mappings().all()]
    return FavoritesResponse(items=items, total=len(items))


async def add_favorite(session: AsyncSession, question_id: str, user_id: str) -> FavoriteToggleResponse | None:
    async with session.begin():
        question_exists_result = await session.execute(
            text(
                """
                SELECT EXISTS (
                  SELECT 1
                  FROM questions
                  WHERE id = CAST(:question_id AS uuid) AND is_active = true
                )
                """
            ),
            {"question_id": question_id},
        )
        if not question_exists_result.scalar_one():
            return None

        await session.execute(
            text(
                """
                INSERT INTO favorite_questions (user_id, question_id)
                VALUES (CAST(:user_id AS uuid), CAST(:question_id AS uuid))
                ON CONFLICT (user_id, question_id) DO NOTHING
                """
            ),
            {"user_id": user_id, "question_id": question_id},
        )

    return FavoriteToggleResponse(question_id=question_id, is_favorited=True)


async def remove_favorite(session: AsyncSession, question_id: str, user_id: str) -> FavoriteToggleResponse:
    async with session.begin():
        await session.execute(
            text(
                """
                DELETE FROM favorite_questions
                WHERE user_id = CAST(:user_id AS uuid) AND question_id = CAST(:question_id AS uuid)
                """
            ),
            {"user_id": user_id, "question_id": question_id},
        )
    return FavoriteToggleResponse(question_id=question_id, is_favorited=False)


def row_to_favorite_item(row) -> FavoriteQuestionItem:
    difficulty = row["difficulty"]
    return FavoriteQuestionItem(
        id=row["favorite_id"],
        created_at=row["created_at"],
        question={
            "id": row["question_id"],
            "pattern": {
                "id": row["pattern_id"],
                "slug": row["pattern_slug"],
                "name": row["pattern_name"],
                "question_count": 0,
            },
            "difficulty": difficulty,
            "difficulty_label": DIFFICULTY_LABELS.get(difficulty, difficulty),
            "market_regime": row["market_regime"],
            "base_date": row["base_date"],
            "public_accuracy": float(row["public_accuracy"]) if row["public_accuracy"] is not None else None,
            "total_answers": row["total_answers"],
            "is_favorited": True,
        },
    )
