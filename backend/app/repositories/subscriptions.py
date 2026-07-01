from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.answers import DEV_USER_ID
from app.schemas import SubscriptionResponse


async def get_my_subscription(session: AsyncSession) -> SubscriptionResponse:
    result = await session.execute(
        text(
            """
            SELECT
              u.plan::text AS user_plan,
              u.daily_question_limit,
              u.streak_days,
              COALESCE(s.plan::text, u.plan::text) AS plan,
              COALESCE(s.status::text, 'active') AS status,
              (
                SELECT COUNT(*)::int
                FROM user_answers a
                WHERE a.user_id = u.id AND a.created_at >= date_trunc('day', now())
              ) AS solved_today
            FROM users u
            LEFT JOIN subscriptions s
              ON s.user_id = u.id
              AND s.status IN ('trialing', 'active')
            WHERE u.id = CAST(:user_id AS uuid)
            ORDER BY s.created_at DESC NULLS LAST
            LIMIT 1
            """
        ),
        {"user_id": DEV_USER_ID},
    )
    row = result.mappings().first()
    if row is None:
        return SubscriptionResponse(
            plan="free",
            status="active",
            daily_question_limit=10,
            solved_today=0,
            remaining_today=10,
            streak_days=0,
        )

    limit = row["daily_question_limit"]
    solved_today = row["solved_today"]
    return SubscriptionResponse(
        plan=row["plan"],
        status=row["status"],
        daily_question_limit=limit,
        solved_today=solved_today,
        remaining_today=max(limit - solved_today, 0),
        streak_days=row["streak_days"],
    )
