from fastapi import APIRouter

from app.mock_data import PATTERNS

router = APIRouter()


@router.get("")
async def list_patterns() -> list[dict]:
    return PATTERNS


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
