from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.db.database import get_session
from app.repositories import wrong_notes as wrong_notes_repository
from app.schemas import WrongNoteDetailResponse, WrongNotesResponse

router = APIRouter()


@router.get("")
async def list_wrong_notes(
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> WrongNotesResponse:
    return await wrong_notes_repository.list_wrong_notes(session, limit, offset, current_user.id)


@router.get("/{answer_id}")
async def get_wrong_note(
    answer_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> WrongNoteDetailResponse:
    wrong_note = await wrong_notes_repository.get_wrong_note(session, answer_id, current_user.id)
    if wrong_note is None:
        raise HTTPException(status_code=404, detail="Wrong note not found")
    return wrong_note
