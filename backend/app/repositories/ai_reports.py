import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.schemas import AiReportGenerateResponse, AiReportResponse
from app.services.openai_reports import generate_openai_report

MIN_OPENAI_ANSWER_COUNT = 3


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

    summary = await get_answer_summary(session, user_id, period_start, period_end)
    patterns = await get_pattern_summaries(session, user_id, period_start, period_end)
    recent_answers = await get_recent_answers(session, user_id, period_start, period_end)

    answer_count = summary["answer_count"]
    accuracy = summary["accuracy"]
    overall_score = min(100, round(accuracy * 80 + min(answer_count, 20)))
    weakest = patterns[0] if patterns else None
    pattern_accuracy = build_pattern_accuracy(patterns)
    trait_scores = build_rule_trait_scores(summary, answer_count, accuracy)
    recommendations = build_recommendations(weakest)
    report_summary = build_summary(answer_count, accuracy, weakest)
    model_name = "rule-based-v1-fallback"

    if answer_count < MIN_OPENAI_ANSWER_COUNT:
        report_summary = build_insufficient_summary(answer_count)
        recommendations = build_insufficient_recommendations()
        model_name = "data-insufficient-v1"
    else:
        try:
            ai_report = await generate_openai_report(
                {
                    "period_start": period_start,
                    "period_end": period_end,
                    "answer_count": answer_count,
                    "accuracy": round(accuracy, 4),
                    "average_duration_ms": summary["average_duration_ms"],
                    "pattern_accuracy": pattern_accuracy,
                    "recent_answers": recent_answers,
                    "service_policy": "학습 피드백 전용. 투자 조언, 매수/매도 추천, 수익 예측 금지.",
                }
            )
        except Exception:
            ai_report = None

        if ai_report is not None:
            report_summary = ai_report["summary"]
            trait_scores = ai_report["trait_scores"]
            recommendations = ai_report["recommendations"]
            model_name = settings_model_name()

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
            "summary": report_summary,
            "recommendations": json.dumps(recommendations, ensure_ascii=False),
            "model_name": model_name,
        },
    )
    row = insert_result.mappings().one()
    await session.commit()

    return AiReportGenerateResponse(report=row_to_report(row))


async def get_answer_summary(session: AsyncSession, user_id: str, period_start, period_end) -> dict[str, Any]:
    result = await session.execute(
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
    return dict(result.mappings().one())


async def get_pattern_summaries(session: AsyncSession, user_id: str, period_start, period_end) -> list[dict[str, Any]]:
    result = await session.execute(
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
    return [dict(row) for row in result.mappings().all()]


async def get_recent_answers(session: AsyncSession, user_id: str, period_start, period_end) -> list[dict[str, Any]]:
    result = await session.execute(
        text(
            """
            SELECT
              p.slug AS pattern_slug,
              p.name AS pattern_name,
              q.difficulty::text AS difficulty,
              a.selected_answer::text AS selected_answer,
              q.correct_answer::text AS correct_answer,
              a.is_correct,
              a.confidence,
              a.reason_tags,
              a.answer_duration_ms,
              a.created_at::text AS created_at
            FROM user_answers a
            JOIN questions q ON q.id = a.question_id
            JOIN patterns p ON p.id = q.pattern_id
            WHERE a.user_id = CAST(:user_id AS uuid)
              AND a.created_at::date BETWEEN :period_start AND :period_end
            ORDER BY a.created_at DESC
            LIMIT 30
            """
        ),
        {"user_id": user_id, "period_start": period_start, "period_end": period_end},
    )
    return [dict(row) for row in result.mappings().all()]


def build_summary(answer_count: int, accuracy: float, weakest: dict[str, Any] | None) -> str:
    if answer_count == 0:
        return "아직 분석할 답안 기록이 없습니다. 먼저 문제를 풀면 리포트가 더 정확해집니다."
    if weakest:
        return (
            f"최근 {answer_count}개 답안 기준 정답률은 {round(accuracy * 100)}%입니다. "
            f"가장 보완이 필요한 패턴은 {weakest['name']}입니다."
        )
    return f"최근 {answer_count}개 답안 기준 정답률은 {round(accuracy * 100)}%입니다."


def build_insufficient_summary(answer_count: int) -> str:
    remaining = max(0, MIN_OPENAI_ANSWER_COUNT - answer_count)
    return (
        f"최근 30일 답안이 {answer_count}개라 AI 분석을 만들기에는 아직 데이터가 부족합니다. "
        f"{remaining}문제를 더 풀면 패턴별 약점과 풀이 성향을 더 정확히 분석할 수 있습니다."
    )


def build_pattern_accuracy(patterns: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        item["slug"]: {
            "name": item["name"],
            "solved_count": item["solved_count"],
            "correct_count": item["correct_count"],
            "accuracy": round(item["accuracy"], 4),
        }
        for item in patterns
    }


def build_rule_trait_scores(summary: dict[str, Any], answer_count: int, accuracy: float) -> dict[str, int]:
    return {
        "trend_reading": min(100, round(accuracy * 100)),
        "speed_control": 70 if summary["average_duration_ms"] <= 20000 else 55,
        "consistency": min(100, 40 + answer_count * 3),
    }


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


def build_insufficient_recommendations() -> list[dict[str, str]]:
    return [
        {
            "title": "최소 3문제 풀기",
            "description": "AI 분석을 시작하려면 최근 답안 기록이 조금 더 필요합니다.",
            "href": "/play",
        },
        {
            "title": "패턴별 훈련장",
            "description": "한 가지 패턴을 연속으로 풀면 분석 품질이 더 좋아집니다.",
            "href": "/patterns",
        },
    ]


def settings_model_name() -> str:
    return settings.openai_model.strip() or "openai"


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
