from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.db.database import get_session
from app.repositories import ai_reports as ai_reports_repository
from app.schemas import AiReportGenerateResponse, AiReportResponse

router = APIRouter()


@router.get("/latest")
async def get_latest_report(
    session: AsyncSession = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> AiReportResponse:
    report = await ai_reports_repository.get_latest_report(session, current_user.id)
    if report is None:
        raise HTTPException(status_code=404, detail="AI report not found")
    return report


@router.post("/generate")
async def generate_report(
    session: AsyncSession = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> AiReportGenerateResponse:
    return await ai_reports_repository.generate_report(session, current_user.id)
