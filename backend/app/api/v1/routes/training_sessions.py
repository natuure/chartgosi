from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.db.database import get_session
from app.repositories import training_sessions as training_sessions_repository
from app.schemas import TrainingSessionDetailResponse, TrainingSessionsResponse

router = APIRouter()


@router.get("/recent")
async def list_recent_training_sessions(
    limit: int = Query(default=20, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> TrainingSessionsResponse:
    return await training_sessions_repository.list_recent_sessions(session, current_user.id, limit)


@router.get("/{session_id}")
async def get_training_session_detail(
    session_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> TrainingSessionDetailResponse:
    result = await training_sessions_repository.get_session_detail(session, current_user.id, session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Training session not found")
    return result
