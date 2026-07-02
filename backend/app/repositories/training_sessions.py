from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import answers as answers_repository
from app.schemas import TrainingSessionDetailResponse, TrainingSessionsResponse


async def list_recent_sessions(session: AsyncSession, user_id: str, limit: int) -> TrainingSessionsResponse:
    count_result = await session.execute(
        text(
            """
            SELECT COUNT(DISTINCT session_id)::int
            FROM user_answers
            WHERE user_id = CAST(:user_id AS uuid)
              AND session_id IS NOT NULL
            """
        ),
        {"user_id": user_id},
    )
    total = count_result.scalar_one() or 0

    result = await session.execute(
        text(
            """
            SELECT
              a.session_id::text AS session_id,
              MIN(a.created_at)::text AS started_at,
              MAX(a.created_at)::text AS last_answered_at,
              COUNT(*)::int AS solved_count,
              SUM(CASE WHEN a.is_correct THEN 1 ELSE 0 END)::int AS correct_count,
              AVG(CASE WHEN a.is_correct THEN 1.0 ELSE 0.0 END)::float AS accuracy,
              p.id::text AS pattern_id,
              p.slug AS pattern_slug,
              p.name AS pattern_name
            FROM user_answers a
            JOIN questions q ON q.id = a.question_id
            JOIN patterns p ON p.id = q.pattern_id
            WHERE a.user_id = CAST(:user_id AS uuid)
              AND a.session_id IS NOT NULL
            GROUP BY a.session_id, p.id, p.slug, p.name
            ORDER BY MAX(a.created_at) DESC
            LIMIT :limit
            """
        ),
        {"user_id": user_id, "limit": limit},
    )

    items = [_to_session_summary(row) for row in result.mappings().all()]
    return {"items": items, "total": total, "limit": limit}


async def get_session_detail(session: AsyncSession, user_id: str, session_id: str) -> TrainingSessionDetailResponse | None:
    summary_result = await session.execute(
        text(
            """
            SELECT
              a.session_id::text AS session_id,
              MIN(a.created_at)::text AS started_at,
              MAX(a.created_at)::text AS last_answered_at,
              COUNT(*)::int AS solved_count,
              SUM(CASE WHEN a.is_correct THEN 1 ELSE 0 END)::int AS correct_count,
              AVG(CASE WHEN a.is_correct THEN 1.0 ELSE 0.0 END)::float AS accuracy,
              p.id::text AS pattern_id,
              p.slug AS pattern_slug,
              p.name AS pattern_name
            FROM user_answers a
            JOIN questions q ON q.id = a.question_id
            JOIN patterns p ON p.id = q.pattern_id
            WHERE a.user_id = CAST(:user_id AS uuid)
              AND a.session_id = CAST(:session_id AS uuid)
            GROUP BY a.session_id, p.id, p.slug, p.name
            LIMIT 1
            """
        ),
        {"user_id": user_id, "session_id": session_id},
    )
    summary_row = summary_result.mappings().first()
    if summary_row is None:
        return None

    answer_ids_result = await session.execute(
        text(
            """
            SELECT id::text
            FROM user_answers
            WHERE user_id = CAST(:user_id AS uuid)
              AND session_id = CAST(:session_id AS uuid)
            ORDER BY created_at ASC
            """
        ),
        {"user_id": user_id, "session_id": session_id},
    )
    answer_ids = [row[0] for row in answer_ids_result.all()]
    answers = []
    for answer_id in answer_ids:
        answer = await answers_repository.get_answer_result(session, answer_id, user_id)
        if answer is not None:
            answers.append(answer)

    return {"session": _to_session_summary(summary_row), "answers": answers}


def _to_session_summary(row) -> dict:
    return {
        "session_id": row["session_id"],
        "pattern": {
            "id": row["pattern_id"],
            "slug": row["pattern_slug"],
            "name": row["pattern_name"],
            "question_count": 0,
        },
        "started_at": row["started_at"],
        "last_answered_at": row["last_answered_at"],
        "solved_count": row["solved_count"],
        "correct_count": row["correct_count"],
        "accuracy": round(row["accuracy"] or 0, 4),
    }
