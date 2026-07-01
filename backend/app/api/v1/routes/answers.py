from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.db.database import get_session
from app.repositories import answers as answers_repository
from app.schemas import AnswerResultResponse

router = APIRouter()


@router.get("/{answer_id}/result")
async def get_answer_result(
    answer_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> AnswerResultResponse:
    result = await answers_repository.get_answer_result(session, answer_id, current_user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="Answer not found")
    return result


@router.patch("/{answer_id}/explanation-viewed")
async def mark_explanation_viewed(
    answer_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    updated = await answers_repository.mark_explanation_viewed(session, answer_id, current_user.id)
    if not updated:
        raise HTTPException(status_code=404, detail="Answer not found")
    return {"answer_id": answer_id, "viewed_ai_explanation": True}
