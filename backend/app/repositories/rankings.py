from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.schemas import MyRankingResponse, RankingPeriodType, RankingsResponse


async def list_rankings(
    session: AsyncSession,
    period_type: RankingPeriodType,
    limit: int,
) -> RankingsResponse:
    result = await session.execute(
        text(
            """
            WITH user_scores AS (
              SELECT
                u.id::text AS user_id,
                u.nickname,
                COUNT(a.id)::int AS solved_count,
                COALESCE(SUM(CASE WHEN a.is_correct THEN 1 ELSE 0 END), 0)::int AS correct_count,
                COALESCE(AVG(CASE WHEN a.is_correct THEN 1.0 ELSE 0.0 END), 0)::float AS accuracy
              FROM users u
              JOIN user_answers a ON a.user_id = u.id
              WHERE (CAST(:period_start AS timestamptz) IS NULL OR a.created_at >= CAST(:period_start AS timestamptz))
              GROUP BY u.id, u.nickname
            ),
            ranked AS (
              SELECT
                ROW_NUMBER() OVER (
                  ORDER BY (correct_count * 10 + solved_count * 2) DESC, accuracy DESC, solved_count DESC, nickname ASC
                )::int AS rank,
                user_id,
                nickname,
                (correct_count * 10 + solved_count * 2)::int AS score,
                accuracy,
                solved_count,
                correct_count
              FROM user_scores
            )
            SELECT *
            FROM ranked
            ORDER BY rank ASC
            LIMIT :limit
            """
        ),
        {"period_start": period_start_for(period_type), "limit": limit},
    )

    return RankingsResponse(
        period_type=period_type,
        items=[ranking_item_from_row(row) for row in result.mappings().all()],
    )


async def get_my_ranking(session: AsyncSession, period_type: RankingPeriodType, user: CurrentUser) -> MyRankingResponse:
    result = await session.execute(
        text(
            """
            WITH user_scores AS (
              SELECT
                u.id::text AS user_id,
                u.nickname,
                COUNT(a.id)::int AS solved_count,
                COALESCE(SUM(CASE WHEN a.is_correct THEN 1 ELSE 0 END), 0)::int AS correct_count,
                COALESCE(AVG(CASE WHEN a.is_correct THEN 1.0 ELSE 0.0 END), 0)::float AS accuracy
              FROM users u
              LEFT JOIN user_answers a
                ON a.user_id = u.id
                AND (CAST(:period_start AS timestamptz) IS NULL OR a.created_at >= CAST(:period_start AS timestamptz))
              GROUP BY u.id, u.nickname
            ),
            ranked AS (
              SELECT
                ROW_NUMBER() OVER (
                  ORDER BY (correct_count * 10 + solved_count * 2) DESC, accuracy DESC, solved_count DESC, nickname ASC
                )::int AS rank,
                user_id,
                nickname,
                (correct_count * 10 + solved_count * 2)::int AS score,
                accuracy,
                solved_count,
                correct_count
              FROM user_scores
            )
            SELECT *
            FROM ranked
            WHERE user_id = :user_id
            LIMIT 1
            """
        ),
        {"period_start": period_start_for(period_type), "user_id": user.id},
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


def period_start_for(period_type: RankingPeriodType) -> datetime | None:
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
