from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.repositories import favorites as favorites_repository
from app.schemas import FavoritesResponse

router = APIRouter()


@router.get("")
async def list_favorites(session: AsyncSession = Depends(get_session)) -> FavoritesResponse:
    return await favorites_repository.list_favorites(session)
