import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import AiReportGenerateResponse, AiReportResponse


async def get_latest_report(session: AsyncSession, user_id: str) -> AiReportResponse | None:
    result = await session.execute(
        text(
            """
            SELECT
              id::text AS id,
              status::text AS status,
              period_start::text AS period_start,
              period_end::text AS period_end,
              answer_count,
              overall_score,
              percentile::float AS percentile,
              pattern_accuracy,
              trait_scores,
              summary,
              recommendations,
              model_name,
              created_at::text AS created_at
            FROM ai_reports
            WHERE user_id = CAST(:user_id AS uuid)
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"user_id": user_id},
    )
    row = result.mappings().first()
    if row is None:
        return None
    return row_to_report(row)


async def generate_report(session: AsyncSession, user_id: str) -> AiReportGenerateResponse:
    period_end = datetime.now(UTC).date()
    period_start = period_end - timedelta(days=30)

    async with session.begin():
        summary_result = await session.execute(
            text(
                """
                SELECT
                  COUNT(*)::int AS answer_count,
                  COALESCE(AVG(CASE WHEN is_correct THEN 1.0 ELSE 0.0 END), 0)::float AS accuracy,
                  COALESCE(AVG(answer_duration_ms), 0)::int AS average_duration_ms
                FROM user_answers
                WHERE user_id = CAST(:user_id AS uuid)
                  AND created_at::date BETWEEN :period_start AND :period_end
                """
            ),
            {"user_id": user_id, "period_start": period_start, "period_end": period_end},
        )
        summary = summary_result.mappings().one()

        pattern_result = await session.execute(
            text(
                """
                SELECT
                  p.slug,
                  p.name,
                  COUNT(a.id)::int AS solved_count,
                  COALESCE(SUM(CASE WHEN a.is_correct THEN 1 ELSE 0 END), 0)::int AS correct_count,
                  COALESCE(AVG(CASE WHEN a.is_correct THEN 1.0 ELSE 0.0 END), 0)::float AS accuracy
                FROM user_answers a
                JOIN questions q ON q.id = a.question_id
                JOIN patterns p ON p.id = q.pattern_id
                WHERE a.user_id = CAST(:user_id AS uuid)
                  AND a.created_at::date BETWEEN :period_start AND :period_end
                GROUP BY p.slug, p.name, p.sort_order
                ORDER BY accuracy ASC, solved_count DESC, p.sort_order ASC
                """
            ),
            {"user_id": user_id, "period_start": period_start, "period_end": period_end},
        )
        patterns = [dict(row) for row in pattern_result.mappings().all()]

        answer_count = summary["answer_count"]
        accuracy = summary["accuracy"]
        overall_score = min(100, round(accuracy * 80 + min(answer_count, 20)))
        weakest = patterns[0] if patterns else None
        pattern_accuracy = {
            item["slug"]: {
                "name": item["name"],
                "solved_count": item["solved_count"],
                "correct_count": item["correct_count"],
                "accuracy": round(item["accuracy"], 4),
            }
            for item in patterns
        }
        trait_scores = {
            "trend_reading": min(100, round(accuracy * 100)),
            "speed_control": 70 if summary["average_duration_ms"] <= 20000 else 55,
            "consistency": min(100, 40 + answer_count * 3),
        }
        recommendations = build_recommendations(weakest)

        insert_result = await session.execute(
            text(
                """
                INSERT INTO ai_reports (
                  user_id,
                  status,
                  period_start,
                  period_end,
                  answer_count,
                  overall_score,
                  percentile,
                  pattern_accuracy,
                  trait_scores,
                  summary,
                  recommendations,
                  model_name
                )
                VALUES (
                  CAST(:user_id AS uuid),
                  'completed',
                  :period_start,
                  :period_end,
                  :answer_count,
                  :overall_score,
                  :percentile,
                  CAST(:pattern_accuracy AS jsonb),
                  CAST(:trait_scores AS jsonb),
                  :summary,
                  CAST(:recommendations AS jsonb),
                  :model_name
                )
                RETURNING
                  id::text AS id,
                  status::text AS status,
                  period_start::text AS period_start,
                  period_end::text AS period_end,
                  answer_count,
                  overall_score,
                  percentile::float AS percentile,
                  pattern_accuracy,
                  trait_scores,
                  summary,
                  recommendations,
                  model_name,
                  created_at::text AS created_at
                """
            ),
            {
                "user_id": user_id,
                "period_start": period_start,
                "period_end": period_end,
                "answer_count": answer_count,
                "overall_score": overall_score,
                "percentile": max(1, 100 - overall_score),
                "pattern_accuracy": json.dumps(pattern_accuracy, ensure_ascii=False),
                "trait_scores": json.dumps(trait_scores, ensure_ascii=False),
                "summary": build_summary(answer_count, accuracy, weakest),
                "recommendations": json.dumps(recommendations, ensure_ascii=False),
                "model_name": "rule-based-v1",
            },
        )
        row = insert_result.mappings().one()

    return AiReportGenerateResponse(report=row_to_report(row))


def build_summary(answer_count: int, accuracy: float, weakest: dict[str, Any] | None) -> str:
    if answer_count == 0:
        return "아직 분석할 답안 기록이 없습니다. 먼저 문제를 풀면 리포트가 더 정확해집니다."
    if weakest:
        return (
            f"최근 {answer_count}개 답안 기준 정답률은 {round(accuracy * 100)}%입니다. "
            f"가장 보완이 필요한 패턴은 {weakest['name']}입니다."
        )
    return f"최근 {answer_count}개 답안 기준 정답률은 {round(accuracy * 100)}%입니다."


def build_recommendations(weakest: dict[str, Any] | None) -> list[dict[str, str]]:
    if weakest is None:
        return [
            {
                "title": "첫 문제 풀기",
                "description": "AI 리포트를 만들기 위해 오늘의 문제를 먼저 풀어보세요.",
                "href": "/play",
            }
        ]
    return [
        {
            "title": f"{weakest['name']} 집중 훈련",
            "description": "정답률이 낮은 패턴을 반복하면 전체 점수가 빠르게 올라갑니다.",
            "href": f"/play?pattern={weakest['slug']}",
        }
    ]


def row_to_report(row) -> AiReportResponse:
    return AiReportResponse(
        id=row["id"],
        status=row["status"],
        period_start=row["period_start"],
        period_end=row["period_end"],
        answer_count=row["answer_count"],
        overall_score=row["overall_score"],
        percentile=row["percentile"],
        pattern_accuracy=row["pattern_accuracy"],
        trait_scores=row["trait_scores"],
        summary=row["summary"],
        recommendations=row["recommendations"],
        model_name=row["model_name"],
        created_at=row["created_at"],
    )
