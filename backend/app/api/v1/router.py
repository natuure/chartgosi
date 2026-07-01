from fastapi import APIRouter

from app.api.v1.routes import ai_reports, answers, favorites, patterns, questions, rankings, stats, subscriptions, wrong_notes

api_router = APIRouter()
api_router.include_router(patterns.router, prefix="/patterns", tags=["patterns"])
api_router.include_router(questions.router, prefix="/questions", tags=["questions"])
api_router.include_router(answers.router, prefix="/answers", tags=["answers"])
api_router.include_router(wrong_notes.router, prefix="/wrong-notes", tags=["wrong-notes"])
api_router.include_router(rankings.router, prefix="/rankings", tags=["rankings"])
api_router.include_router(stats.router, prefix="/stats", tags=["stats"])
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
api_router.include_router(favorites.router, prefix="/favorites", tags=["favorites"])
api_router.include_router(ai_reports.router, prefix="/ai-reports", tags=["ai-reports"])
