from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.db.database import get_session
from app.repositories import question_review as question_review_repository
from app.schemas import QuestionReviewUpdate, ReviewDashboardResponse, ReviewQuestionsResponse, ReviewQuestionItem, ReviewStatus

router = APIRouter()


@router.get("/dashboard")
async def get_review_dashboard(
    session: AsyncSession = Depends(get_session),
    _current_user: CurrentUser = Depends(get_current_user),
) -> ReviewDashboardResponse:
    return await question_review_repository.get_review_dashboard(session)


@router.get("/questions")
async def list_review_questions(
    pattern_slug: str | None = None,
    review_status: ReviewStatus | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    _current_user: CurrentUser = Depends(get_current_user),
) -> ReviewQuestionsResponse:
    return await question_review_repository.list_review_questions(
        session,
        pattern_slug=pattern_slug,
        review_status=review_status,
        limit=limit,
        offset=offset,
    )


@router.patch("/questions/{question_id}")
async def update_question_review(
    question_id: str,
    payload: QuestionReviewUpdate,
    session: AsyncSession = Depends(get_session),
    _current_user: CurrentUser = Depends(get_current_user),
) -> ReviewQuestionItem:
    question = await question_review_repository.update_question_review(session, question_id, payload)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return question
