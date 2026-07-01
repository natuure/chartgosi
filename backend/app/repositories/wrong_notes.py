from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import WrongNoteDetailResponse, WrongNoteItem, WrongNotesResponse


DIFFICULTY_LABELS = {
    "easy": "초급",
    "medium": "중급",
    "hard": "고급",
}


async def list_wrong_notes(session: AsyncSession, limit: int, offset: int, user_id: str) -> WrongNotesResponse:
    count_result = await session.execute(
        text(
            """
            SELECT COUNT(DISTINCT question_id)::int
            FROM user_answers
            WHERE user_id = CAST(:user_id AS uuid) AND is_correct = false
            """
        ),
        {"user_id": user_id},
    )
    total = count_result.scalar_one()

    result = await session.execute(
        text(
            """
            WITH latest_wrong AS (
              SELECT DISTINCT ON (a.question_id)
                a.id::text AS answer_id,
                a.question_id::text AS question_id,
                a.selected_answer::text AS selected_answer,
                a.correct_answer::text AS correct_answer,
                a.created_at AS created_at_value,
                a.created_at::text AS created_at,
                a.viewed_ai_explanation,
                q.difficulty::text AS difficulty,
                q.base_date::text AS base_date,
                q.ai_explanation,
                p.id::text AS pattern_id,
                p.slug AS pattern_slug,
                p.name AS pattern_name
              FROM user_answers a
              JOIN questions q ON q.id = a.question_id
              JOIN patterns p ON p.id = q.pattern_id
              WHERE a.user_id = CAST(:user_id AS uuid) AND a.is_correct = false
              ORDER BY a.question_id, a.created_at DESC
            )
            SELECT *
            FROM latest_wrong
            ORDER BY created_at_value DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"user_id": user_id, "limit": limit, "offset": offset},
    )

    return WrongNotesResponse(
        items=[row_to_wrong_note_item(row) for row in result.mappings().all()],
        total=total,
        limit=limit,
        offset=offset,
    )


async def get_wrong_note(session: AsyncSession, answer_id: str, user_id: str) -> WrongNoteDetailResponse | None:
    result = await session.execute(
        text(
            """
            SELECT
              a.id::text AS answer_id,
              a.question_id::text AS question_id,
              a.selected_answer::text AS selected_answer,
              a.correct_answer::text AS correct_answer,
              a.created_at::text AS created_at,
              a.viewed_ai_explanation,
              q.difficulty::text AS difficulty,
              q.base_date::text AS base_date,
              q.ai_explanation,
              q.actual_next_candles,
              p.id::text AS pattern_id,
              p.slug AS pattern_slug,
              p.name AS pattern_name
            FROM user_answers a
            JOIN questions q ON q.id = a.question_id
            JOIN patterns p ON p.id = q.pattern_id
            WHERE
              a.id = CAST(:answer_id AS uuid)
              AND a.user_id = CAST(:user_id AS uuid)
              AND a.is_correct = false
            LIMIT 1
            """
        ),
        {"answer_id": answer_id, "user_id": user_id},
    )
    row = result.mappings().first()
    if row is None:
        return None

    item = row_to_wrong_note_item(row)
    return WrongNoteDetailResponse(
        **item.model_dump(),
        actual_next_candles=row["actual_next_candles"],
    )


def row_to_wrong_note_item(row) -> WrongNoteItem:
    difficulty = row["difficulty"]
    return WrongNoteItem(
        answer_id=row["answer_id"],
        question_id=row["question_id"],
        pattern={
            "id": row["pattern_id"],
            "slug": row["pattern_slug"],
            "name": row["pattern_name"],
            "question_count": 0,
        },
        difficulty=difficulty,
        difficulty_label=DIFFICULTY_LABELS.get(difficulty, difficulty),
        base_date=row["base_date"],
        selected_answer=row["selected_answer"],
        correct_answer=row["correct_answer"],
        created_at=row["created_at"],
        viewed_ai_explanation=row["viewed_ai_explanation"],
        ai_explanation=row["ai_explanation"],
    )
