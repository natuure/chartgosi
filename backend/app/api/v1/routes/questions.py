from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user, get_optional_current_user
from app.db.database import get_session
from app.repositories import answers as answers_repository
from app.repositories import favorites as favorites_repository
from app.repositories import questions as questions_repository
from app.schemas import AnswerSubmit, AnswerSubmitResponse, FavoriteToggleResponse, QuestionResponse

router = APIRouter()


@router.get("/today")
async def get_today_question(
    pattern_slug: str | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: CurrentUser | None = Depends(get_optional_current_user),
) -> QuestionResponse:
    question = await questions_repository.get_today_question(session, pattern_slug, current_user.id if current_user else None)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@router.get("/{question_id}")
async def get_question(
    question_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: CurrentUser | None = Depends(get_optional_current_user),
) -> QuestionResponse:
    question = await questions_repository.get_question(session, question_id, current_user.id if current_user else None)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@router.post("/{question_id}/answers", status_code=201)
async def submit_answer(
    question_id: str,
    payload: AnswerSubmit,
    session: AsyncSession = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> AnswerSubmitResponse:
    answer = await answers_repository.submit_answer(session, question_id, payload, current_user.id)
    if answer is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return answer


@router.post("/{question_id}/favorite")
async def add_favorite(
    question_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> FavoriteToggleResponse:
    result = await favorites_repository.add_favorite(session, question_id, current_user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return result


@router.delete("/{question_id}/favorite")
async def remove_favorite(
    question_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> FavoriteToggleResponse:
    return await favorites_repository.remove_favorite(session, question_id, current_user.id)
