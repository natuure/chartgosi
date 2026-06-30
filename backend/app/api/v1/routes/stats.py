from fastapi import APIRouter

router = APIRouter()


@router.get("/me")
async def get_my_stats() -> dict:
    return {
        "solved_count": 100,
        "accuracy": 0.7,
        "average_duration_ms": 18200,
        "pattern_accuracy": {
            "cup-and-handle": 0.89,
            "double-bottom": 0.78,
            "volume-spike": 0.45,
        },
    }
