from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_wrong_notes() -> dict:
    return {"items": [], "total": 0}


@router.get("/{answer_id}")
async def get_wrong_note(answer_id: str) -> dict:
    return {"answer_id": answer_id, "status": "placeholder"}
