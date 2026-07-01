from fastapi import APIRouter, HTTPException, Query
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_optional_current_user
from app.db.database import get_session
from app.repositories import patterns as patterns_repository
from app.repositories import questions as questions_repository
from app.schemas import PatternResponse, QuestionListItem, QuestionResponse

router = APIRouter()


@router.get("")
async def list_patterns(session: AsyncSession = Depends(get_session)) -> list[PatternResponse]:
    return await patterns_repository.list_patterns(session)


@router.get("/{pattern_key}/questions")
async def list_pattern_questions(
    pattern_key: str,
    session: AsyncSession = Depends(get_session),
    current_user: CurrentUser | None = Depends(get_optional_current_user),
) -> list[QuestionListItem]:
    return await questions_repository.list_pattern_questions(session, pattern_key, current_user.id if current_user else None)


@router.get("/{pattern_key}/session")
async def list_pattern_session_questions(
    pattern_key: str,
    limit: int = Query(default=5, ge=1, le=10),
    session: AsyncSession = Depends(get_session),
    current_user: CurrentUser | None = Depends(get_optional_current_user),
) -> list[QuestionResponse]:
    questions = await questions_repository.list_pattern_session_questions(
        session,
        pattern_key,
        limit,
        current_user.id if current_user else None,
    )
    if not questions:
        raise HTTPException(status_code=404, detail="Pattern session questions not found")
    return questions
