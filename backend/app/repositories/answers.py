from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import rankings as rankings_repository
from app.schemas import AnswerResultResponse, AnswerSubmit, AnswerSubmitResponse


async def submit_answer(
    session: AsyncSession,
    question_id: str,
    payload: AnswerSubmit,
    user_id: str,
) -> AnswerSubmitResponse | None:
    async with session.begin():
        question_result = await session.execute(
            text(
                """
                SELECT id::text, correct_answer::text
                FROM questions
                WHERE id = CAST(:question_id AS uuid) AND is_active = true
                LIMIT 1
                """
            ),
            {"question_id": question_id},
        )
        question = question_result.mappings().first()
        if question is None:
            return None

        correct_answer = question["correct_answer"]
        is_correct = payload.selected_answer == correct_answer

        insert_result = await insert_user_answer(session, question_id, payload, user_id, correct_answer, is_correct)
        answer_id = insert_result.scalar_one()

        await session.execute(
            text(
                """
                UPDATE questions
                SET
                  total_answers = stats.total_answers,
                  public_accuracy = stats.public_accuracy,
                  updated_at = now()
                FROM (
                  SELECT
                    COUNT(*)::int AS total_answers,
                    AVG(CASE WHEN is_correct THEN 1.0 ELSE 0.0 END)::numeric(5,4) AS public_accuracy
                  FROM user_answers
                  WHERE question_id = CAST(:question_id AS uuid)
                ) stats
                WHERE questions.id = CAST(:question_id AS uuid)
                """
            ),
            {"question_id": question_id},
        )

        await rankings_repository.refresh_user_rankings(session, user_id)

    return AnswerSubmitResponse(
        answer_id=answer_id,
        question_id=question_id,
        selected_answer=payload.selected_answer,
        correct_answer=correct_answer,
        is_correct=is_correct,
    )


async def insert_user_answer(
    session: AsyncSession,
    question_id: str,
    payload: AnswerSubmit,
    user_id: str,
    correct_answer: str,
    is_correct: bool,
):
    params = {
        "user_id": user_id,
        "question_id": question_id,
        "selected_answer": payload.selected_answer,
        "correct_answer": correct_answer,
        "is_correct": is_correct,
        "confidence": payload.confidence,
        "reason_tags": payload.reason_tags,
        "answer_duration_ms": payload.answer_duration_ms,
        "is_retry": payload.is_retry,
    }

    if payload.session_id:
        return await session.execute(
            text(
                """
                INSERT INTO user_answers (
                  user_id,
                  question_id,
                  selected_answer,
                  correct_answer,
                  is_correct,
                  confidence,
                  reason_tags,
                  answer_duration_ms,
                  is_retry,
                  session_id
                )
                VALUES (
                  CAST(:user_id AS uuid),
                  CAST(:question_id AS uuid),
                  CAST(:selected_answer AS answer_direction),
                  CAST(:correct_answer AS answer_direction),
                  :is_correct,
                  :confidence,
                  :reason_tags,
                  :answer_duration_ms,
                  :is_retry,
                  CAST(:session_id AS uuid)
                )
                RETURNING id::text
                """
            ),
            {**params, "session_id": str(payload.session_id)},
        )

    return await session.execute(
        text(
            """
            INSERT INTO user_answers (
              user_id,
              question_id,
              selected_answer,
              correct_answer,
              is_correct,
              confidence,
              reason_tags,
              answer_duration_ms,
              is_retry
            )
            VALUES (
              CAST(:user_id AS uuid),
              CAST(:question_id AS uuid),
              CAST(:selected_answer AS answer_direction),
              CAST(:correct_answer AS answer_direction),
              :is_correct,
              :confidence,
              :reason_tags,
              :answer_duration_ms,
              :is_retry
            )
            RETURNING id::text
            """
        ),
        params,
    )


async def get_answer_result(session: AsyncSession, answer_id: str, user_id: str) -> AnswerResultResponse | None:
    answer_result = await session.execute(
        text(
            """
            SELECT
              a.id::text AS answer_id,
              a.question_id::text AS question_id,
              a.selected_answer::text AS selected_answer,
              a.correct_answer::text AS correct_answer,
              a.is_correct,
              q.actual_next_candles,
              q.ai_explanation,
              q.pattern_evidence,
              q.rule_score,
              q.timeframe,
              p.id::text AS pattern_id,
              p.slug AS pattern_slug,
              p.name AS pattern_name,
              p.description AS pattern_description,
              p.definition AS pattern_definition
            FROM user_answers a
            JOIN questions q ON q.id = a.question_id
            JOIN patterns p ON p.id = q.pattern_id
            WHERE a.id = CAST(:answer_id AS uuid)
              AND a.user_id = CAST(:user_id AS uuid)
            LIMIT 1
            """
        ),
        {"answer_id": answer_id, "user_id": user_id},
    )
    answer = answer_result.mappings().first()
    if answer is None:
        return None

    distribution_result = await session.execute(
        text(
            """
            SELECT selected_answer::text AS selected_answer, COUNT(*)::float AS count
            FROM user_answers
            WHERE question_id = CAST(:question_id AS uuid)
            GROUP BY selected_answer
            """
        ),
        {"question_id": answer["question_id"]},
    )
    counts = {row["selected_answer"]: row["count"] for row in distribution_result.mappings().all()}
    total = sum(counts.values()) or 1.0
    distribution = {key: round(value / total, 4) for key, value in counts.items()}
    for option in ("up", "sideways", "down"):
        distribution.setdefault(option, 0.0)

    return AnswerResultResponse(
        answer_id=answer["answer_id"],
        question_id=answer["question_id"],
        pattern={
            "id": answer["pattern_id"],
            "slug": answer["pattern_slug"],
            "name": answer["pattern_name"],
            "question_count": 0,
            "description": answer["pattern_description"],
            "definition": answer["pattern_definition"],
        },
        timeframe=answer["timeframe"],
        selected_answer=answer["selected_answer"],
        correct_answer=answer["correct_answer"],
        is_correct=answer["is_correct"],
        actual_next_candles=answer["actual_next_candles"],
        ai_explanation=answer["ai_explanation"],
        pattern_evidence=answer["pattern_evidence"] or [],
        pattern_score=float(answer["rule_score"]) if answer["rule_score"] is not None else None,
        choice_distribution=distribution,
    )


async def mark_explanation_viewed(session: AsyncSession, answer_id: str, user_id: str) -> bool:
    async with session.begin():
        result = await session.execute(
            text(
                """
                UPDATE user_answers
                SET viewed_ai_explanation = true, updated_at = now()
                WHERE id = CAST(:answer_id AS uuid)
                  AND user_id = CAST(:user_id AS uuid)
                """
            ),
            {"answer_id": answer_id, "user_id": user_id},
        )
    return result.rowcount > 0
