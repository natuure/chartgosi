from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.db.database import get_session
from app.repositories import stats as stats_repository
from app.schemas import StatsResponse

router = APIRouter()


@router.get("/me")
async def get_my_stats(
    session: AsyncSession = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> StatsResponse:
    return await stats_repository.get_my_stats(session, current_user.id)
