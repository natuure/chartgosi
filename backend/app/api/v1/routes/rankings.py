from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.db.database import get_session
from app.repositories import rankings as rankings_repository
from app.schemas import MyRankingResponse, RankingPeriodType, RankingsResponse

router = APIRouter()


@router.get("")
async def list_rankings(
    period_type: RankingPeriodType = "weekly",
    limit: int = Query(default=30, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> RankingsResponse:
    return await rankings_repository.list_rankings(session, period_type, limit)


@router.get("/me")
async def get_my_ranking(
    period_type: RankingPeriodType = "weekly",
    session: AsyncSession = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> MyRankingResponse:
    return await rankings_repository.get_my_ranking(session, period_type, current_user)
