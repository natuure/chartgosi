from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.answers import DEV_USER_ID
from app.schemas import StatsResponse


async def get_my_stats(session: AsyncSession) -> StatsResponse:
    summary_result = await session.execute(
        text(
            """
            SELECT
              COUNT(*)::int AS solved_count,
              COALESCE(SUM(CASE WHEN is_correct THEN 1 ELSE 0 END), 0)::int AS correct_count,
              COALESCE(SUM(CASE WHEN is_correct THEN 0 ELSE 1 END), 0)::int AS wrong_count,
              COALESCE(AVG(CASE WHEN is_correct THEN 1.0 ELSE 0.0 END), 0)::float AS accuracy,
              AVG(answer_duration_ms)::int AS average_duration_ms
            FROM user_answers
            WHERE user_id = CAST(:user_id AS uuid)
            """
        ),
        {"user_id": DEV_USER_ID},
    )
    summary = summary_result.mappings().one()

    pattern_result = await session.execute(
        text(
            """
            SELECT
              p.id::text AS pattern_id,
              p.slug AS pattern_slug,
              p.name AS pattern_name,
              COUNT(a.id)::int AS solved_count,
              COALESCE(SUM(CASE WHEN a.is_correct THEN 1 ELSE 0 END), 0)::int AS correct_count,
              COALESCE(AVG(CASE WHEN a.is_correct THEN 1.0 ELSE 0.0 END), 0)::float AS accuracy
            FROM user_answers a
            JOIN questions q ON q.id = a.question_id
            JOIN patterns p ON p.id = q.pattern_id
            WHERE a.user_id = CAST(:user_id AS uuid)
            GROUP BY p.id, p.slug, p.name, p.sort_order
            ORDER BY p.sort_order ASC
            """
        ),
        {"user_id": DEV_USER_ID},
    )

    return StatsResponse(
        solved_count=summary["solved_count"],
        correct_count=summary["correct_count"],
        wrong_count=summary["wrong_count"],
        accuracy=round(summary["accuracy"], 4),
        average_duration_ms=summary["average_duration_ms"],
        pattern_stats=[
            {
                "pattern": {
                    "id": row["pattern_id"],
                    "slug": row["pattern_slug"],
                    "name": row["pattern_name"],
                    "question_count": 0,
                },
                "solved_count": row["solved_count"],
                "correct_count": row["correct_count"],
                "accuracy": round(row["accuracy"], 4),
            }
            for row in pattern_result.mappings().all()
        ],
    )
