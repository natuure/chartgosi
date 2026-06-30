from fastapi import APIRouter, HTTPException

from app.mock_data import SAMPLE_QUESTION

router = APIRouter()


@router.get("/today")
async def get_today_question() -> dict:
    return SAMPLE_QUESTION


@router.get("/{question_id}")
async def get_question(question_id: str) -> dict:
    if question_id != SAMPLE_QUESTION["id"]:
        raise HTTPException(status_code=404, detail="Question not found")
    return SAMPLE_QUESTION


@router.post("/{question_id}/answers", status_code=201)
async def submit_answer(question_id: str, payload: dict) -> dict:
    if question_id != SAMPLE_QUESTION["id"]:
        raise HTTPException(status_code=404, detail="Question not found")

    selected_answer = payload.get("selected_answer")
    correct_answer = SAMPLE_QUESTION["correct_answer"]

    return {
        "answer_id": "a_mock_001",
        "question_id": question_id,
        "selected_answer": selected_answer,
        "correct_answer": correct_answer,
        "is_correct": selected_answer == correct_answer,
    }
