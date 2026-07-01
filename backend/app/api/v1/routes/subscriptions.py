from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.repositories import subscriptions as subscriptions_repository
from app.schemas import SubscriptionResponse

router = APIRouter()


@router.get("/me")
async def get_my_subscription(session: AsyncSession = Depends(get_session)) -> SubscriptionResponse:
    return await subscriptions_repository.get_my_subscription(session)
