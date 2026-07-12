import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.questions import DIFFICULTY_LABELS
from app.schemas import QuestionReviewUpdate, ReviewQuestionItem, ReviewQuestionsResponse


async def list_review_questions(
    session: AsyncSession,
    pattern_slug: str | None = None,
    review_status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> ReviewQuestionsResponse:
    filters = [
        "q.is_active = true",
        "p.is_active = true",
        "(CAST(:pattern_slug AS text) IS NULL OR p.slug = CAST(:pattern_slug AS text))",
        "(CAST(:review_status AS text) IS NULL OR q.review_status = CAST(:review_status AS text))",
    ]
    where_sql = " AND ".join(filters)
    params = {
        "pattern_slug": pattern_slug,
        "review_status": review_status,
        "limit": limit,
        "offset": offset,
    }

    total_result = await session.execute(
        text(
            f"""
            SELECT COUNT(*)::int
            FROM questions q
            JOIN patterns p ON p.id = q.pattern_id
            WHERE {where_sql}
            """
        ),
        params,
    )
    total = int(total_result.scalar_one())

    result = await session.execute(
        text(
            f"""
            SELECT
              q.id::text AS id,
              q.difficulty::text AS difficulty,
              q.market_regime::text AS market_regime,
              q.timeframe,
              q.base_date::text AS base_date,
              q.chart_data,
              q.actual_next_candles,
              q.correct_answer::text AS correct_answer,
              q.pattern_evidence,
              q.pattern_score_breakdown,
              q.pattern_markers,
              q.review_status,
              q.review_note,
              q.is_synthetic,
              q.source_name,
              q.source_url,
              q.source_symbol,
              q.source_exchange,
              q.source_date_range,
              q.rule_score,
              q.public_accuracy,
              q.total_answers,
              p.id::text AS pattern_id,
              p.slug AS pattern_slug,
              p.name AS pattern_name,
              p.description AS pattern_description,
              p.definition AS pattern_definition
            FROM questions q
            JOIN patterns p ON p.id = q.pattern_id
            WHERE {where_sql}
            ORDER BY
              CASE q.review_status
                WHEN 'needs_review' THEN 0
                WHEN 'pending' THEN 1
                WHEN 'approved' THEN 2
                ELSE 3
              END,
              p.sort_order ASC,
              q.rule_score DESC NULLS LAST,
              q.created_at ASC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )
    items = [row_to_review_question(row) for row in result.mappings().all()]
    return ReviewQuestionsResponse(items=items, total=total, limit=limit, offset=offset)


async def update_question_review(
    session: AsyncSession,
    question_id: str,
    payload: QuestionReviewUpdate,
) -> ReviewQuestionItem | None:
    params = {
        "question_id": question_id,
        "review_status": payload.review_status,
        "review_note": payload.review_note,
        "pattern_markers": json.dumps(
            [marker.model_dump() for marker in payload.pattern_markers],
            ensure_ascii=False,
        )
        if payload.pattern_markers is not None
        else None,
    }
    async with session.begin():
        update_result = await session.execute(
            text(
                """
                UPDATE questions
                SET
                  review_status = COALESCE(CAST(:review_status AS text), review_status),
                  review_note = COALESCE(CAST(:review_note AS text), review_note),
                  pattern_markers = COALESCE(CAST(:pattern_markers AS jsonb), pattern_markers),
                  updated_at = now()
                WHERE id = CAST(:question_id AS uuid)
                RETURNING id
                """
            ),
            params,
        )
        if update_result.scalar_one_or_none() is None:
            return None

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
              q.actual_next_candles,
              q.correct_answer::text AS correct_answer,
              q.pattern_evidence,
              q.pattern_score_breakdown,
              q.pattern_markers,
              q.review_status,
              q.review_note,
              q.is_synthetic,
              q.source_name,
              q.source_url,
              q.source_symbol,
              q.source_exchange,
              q.source_date_range,
              q.rule_score,
              q.public_accuracy,
              q.total_answers,
              p.id::text AS pattern_id,
              p.slug AS pattern_slug,
              p.name AS pattern_name,
              p.description AS pattern_description,
              p.definition AS pattern_definition
            FROM questions q
            JOIN patterns p ON p.id = q.pattern_id
            WHERE q.id = CAST(:question_id AS uuid)
            LIMIT 1
            """
        ),
        {"question_id": question_id},
    )
    row = result.mappings().first()
    return row_to_review_question(row) if row is not None else None


def row_to_review_question(row) -> ReviewQuestionItem:
    difficulty = row["difficulty"]
    return ReviewQuestionItem(
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
        is_favorited=False,
        pattern_evidence=row["pattern_evidence"] or [],
        pattern_score_breakdown=row["pattern_score_breakdown"],
        pattern_markers=row["pattern_markers"] or [],
        is_synthetic=row["is_synthetic"],
        source_name=row["source_name"],
        source_url=row["source_url"],
        source_symbol=row["source_symbol"],
        source_exchange=row["source_exchange"],
        source_date_range=row["source_date_range"],
        correct_answer=row["correct_answer"],
        actual_next_candles=row["actual_next_candles"] or [],
        review_status=row["review_status"],
        review_note=row["review_note"] or "",
        total_answers=row["total_answers"],
    )
