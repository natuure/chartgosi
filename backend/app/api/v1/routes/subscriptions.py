from fastapi import APIRouter

router = APIRouter()


@router.get("/me")
async def get_my_subscription() -> dict:
    return {"plan": "free", "status": "active", "daily_question_limit": 10}
