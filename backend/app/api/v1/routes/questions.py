from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.repositories import answers as answers_repository
from app.repositories import questions as questions_repository
from app.schemas import AnswerSubmit, AnswerSubmitResponse, QuestionResponse

router = APIRouter()


@router.get("/today")
async def get_today_question(session: AsyncSession = Depends(get_session)) -> QuestionResponse:
    question = await questions_repository.get_today_question(session)
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
