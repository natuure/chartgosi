from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

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
) -> QuestionResponse:
    question = await questions_repository.get_today_question(session, pattern_slug)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@router.get("/{question_id}")
async def get_question(
    question_id: str,
    session: AsyncSession = Depends(get_session),
) -> QuestionResponse:
    question = await questions_repository.get_question(session, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@router.post("/{question_id}/answers", status_code=201)
async def submit_answer(
    question_id: str,
    payload: AnswerSubmit,
    session: AsyncSession = Depends(get_session),
) -> AnswerSubmitResponse:
    answer = await answers_repository.submit_answer(session, question_id, payload)
    if answer is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return answer


@router.post("/{question_id}/favorite")
async def add_favorite(
    question_id: str,
    session: AsyncSession = Depends(get_session),
) -> FavoriteToggleResponse:
    result = await favorites_repository.add_favorite(session, question_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return result


@router.delete("/{question_id}/favorite")
async def remove_favorite(
    question_id: str,
    session: AsyncSession = Depends(get_session),
) -> FavoriteToggleResponse:
    return await favorites_repository.remove_favorite(session, question_id)
