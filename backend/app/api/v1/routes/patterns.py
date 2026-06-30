from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.repositories import patterns as patterns_repository
from app.schemas import PatternResponse

router = APIRouter()


@router.get("")
async def list_patterns(session: AsyncSession = Depends(get_session)) -> list[PatternResponse]:
    return await patterns_repository.list_patterns(session)


@router.get("/{pattern_id}/questions")
async def list_pattern_questions(pattern_id: str) -> dict:
    return {
        "pattern_id": pattern_id,
        "questions": [
            {
                "id": "q_sample_001",
                "difficulty": "medium",
                "public_accuracy": 0.7,
            }
        ],
    }
