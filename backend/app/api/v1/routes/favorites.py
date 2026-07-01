from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.db.database import get_session
from app.repositories import favorites as favorites_repository
from app.schemas import FavoritesResponse

router = APIRouter()


@router.get("")
async def list_favorites(
    session: AsyncSession = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> FavoritesResponse:
    return await favorites_repository.list_favorites(session, current_user.id)
