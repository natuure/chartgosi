from fastapi import APIRouter, HTTPException

from app.mock_data import RESULT

router = APIRouter()


@router.get("/{answer_id}/result")
async def get_answer_result(answer_id: str) -> dict:
    if not answer_id:
        raise HTTPException(status_code=404, detail="Answer not found")
    return {**RESULT, "answer_id": answer_id}


@router.patch("/{answer_id}/explanation-viewed")
async def mark_explanation_viewed(answer_id: str) -> dict:
    return {"answer_id": answer_id, "viewed_ai_explanation": True}
