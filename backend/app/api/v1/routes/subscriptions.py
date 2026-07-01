from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.db.database import get_session
from app.repositories import subscriptions as subscriptions_repository
from app.schemas import SubscriptionResponse

router = APIRouter()


@router.get("/me")
async def get_my_subscription(
    session: AsyncSession = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> SubscriptionResponse:
    return await subscriptions_repository.get_my_subscription(session, current_user.id)
