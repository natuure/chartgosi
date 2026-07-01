from datetime import UTC, date, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.schemas import MyRankingResponse, RankingPeriodType, RankingsResponse

ALL_TIME_PERIOD_START = date(1970, 1, 1)
RANKING_PERIODS: tuple[RankingPeriodType, ...] = ("daily", "weekly", "monthly", "all_time")


async def refresh_user_rankings(session: AsyncSession, user_id: str) -> None:
    for period_type in RANKING_PERIODS:
        await session.execute(
            text(
                """
                INSERT INTO rankings (
                  user_id,
                  period_type,
                  period_start,
                  score,
                  accuracy,
                  solved_count,
                  correct_count,
                  streak_days
                )
                SELECT
                  CAST(:user_id AS uuid),
                  CAST(:period_type AS ranking_period_type),
                  CAST(:period_start AS date),
                  (COALESCE(SUM(CASE WHEN a.is_correct THEN 1 ELSE 0 END), 0) * 10)::int AS score,
                  COALESCE(AVG(CASE WHEN a.is_correct THEN 1.0 ELSE 0.0 END), 0)::numeric(5,4) AS accuracy,
                  COUNT(a.id)::int AS solved_count,
                  COALESCE(SUM(CASE WHEN a.is_correct THEN 1 ELSE 0 END), 0)::int AS correct_count,
                  COALESCE(MAX(u.streak_days), 0)::int AS streak_days
                FROM users u
                LEFT JOIN user_answers a
                  ON a.user_id = u.id
                  AND (CAST(:answer_filter_start AS timestamptz) IS NULL OR a.created_at >= CAST(:answer_filter_start AS timestamptz))
                WHERE u.id = CAST(:user_id AS uuid)
                GROUP BY u.id
                ON CONFLICT (user_id, period_type, period_start) DO UPDATE
                SET
                  score = EXCLUDED.score,
                  accuracy = EXCLUDED.accuracy,
                  solved_count = EXCLUDED.solved_count,
                  correct_count = EXCLUDED.correct_count,
                  streak_days = EXCLUDED.streak_days,
                  updated_at = now()
                """
            ),
            {
                "user_id": user_id,
                "period_type": period_type,
                "period_start": ranking_period_start_for(period_type),
                "answer_filter_start": answer_filter_start_for(period_type),
            },
        )


async def list_rankings(
    session: AsyncSession,
    period_type: RankingPeriodType,
    limit: int,
) -> RankingsResponse:
    result = await session.execute(
        text(
            """
            WITH ranked AS (
              SELECT
                ROW_NUMBER() OVER (
                  ORDER BY r.score DESC, r.accuracy DESC, r.solved_count DESC, u.nickname ASC
                )::int AS rank,
                u.id::text AS user_id,
                u.nickname,
                r.score,
                r.accuracy::float AS accuracy,
                r.solved_count,
                r.correct_count
              FROM rankings r
              JOIN users u ON u.id = r.user_id
              WHERE r.period_type = CAST(:period_type AS ranking_period_type)
                AND r.period_start = CAST(:period_start AS date)
            )
            SELECT *
            FROM ranked
            ORDER BY rank ASC
            LIMIT :limit
            """
        ),
        {"period_type": period_type, "period_start": ranking_period_start_for(period_type), "limit": limit},
    )

    return RankingsResponse(
        period_type=period_type,
        items=[ranking_item_from_row(row) for row in result.mappings().all()],
    )


async def get_my_ranking(session: AsyncSession, period_type: RankingPeriodType, user: CurrentUser) -> MyRankingResponse:
    result = await session.execute(
        text(
            """
            WITH ranked AS (
              SELECT
                ROW_NUMBER() OVER (
                  ORDER BY r.score DESC, r.accuracy DESC, r.solved_count DESC, u.nickname ASC
                )::int AS rank,
                u.id::text AS user_id,
                u.nickname,
                r.score,
                r.accuracy::float AS accuracy,
                r.solved_count,
                r.correct_count
              FROM rankings r
              JOIN users u ON u.id = r.user_id
              WHERE r.period_type = CAST(:period_type AS ranking_period_type)
                AND r.period_start = CAST(:period_start AS date)
            )
            SELECT *
            FROM ranked
            WHERE user_id = :user_id
            LIMIT 1
            """
        ),
        {"period_type": period_type, "period_start": ranking_period_start_for(period_type), "user_id": user.id},
    )
    row = result.mappings().first()

    if row is None:
        return MyRankingResponse(
            period_type=period_type,
            rank=None,
            user_id=user.id,
            nickname=user.nickname,
            score=0,
            accuracy=0,
            solved_count=0,
            correct_count=0,
        )

    return MyRankingResponse(period_type=period_type, **ranking_item_from_row(row))


def ranking_period_start_for(period_type: RankingPeriodType) -> date:
    now = datetime.now(UTC)
    if period_type == "daily":
        return now.date()
    if period_type == "weekly":
        return (now - timedelta(days=now.weekday())).date()
    if period_type == "monthly":
        return now.replace(day=1).date()
    return ALL_TIME_PERIOD_START


def answer_filter_start_for(period_type: RankingPeriodType) -> datetime | None:
    now = datetime.now(UTC)
    if period_type == "daily":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period_type == "weekly":
        start = now - timedelta(days=now.weekday())
        return start.replace(hour=0, minute=0, second=0, microsecond=0)
    if period_type == "monthly":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return None


def ranking_item_from_row(row) -> dict:
    return {
        "rank": row["rank"],
        "user_id": row["user_id"],
        "nickname": row["nickname"],
        "score": row["score"],
        "accuracy": round(row["accuracy"], 4),
        "solved_count": row["solved_count"],
        "correct_count": row["correct_count"],
    }
