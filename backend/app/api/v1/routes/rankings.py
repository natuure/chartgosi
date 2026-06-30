from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_rankings(period_type: str = "weekly") -> dict:
    return {
        "period_type": period_type,
        "items": [
            {"rank": 1, "nickname": "차트마스터", "score": 1200, "accuracy": 0.92, "solved_count": 120},
            {"rank": 2, "nickname": "봉의달인", "score": 1140, "accuracy": 0.89, "solved_count": 108},
            {"rank": 3, "nickname": "추세추종자", "score": 1088, "accuracy": 0.86, "solved_count": 101},
        ],
    }


@router.get("/me")
async def get_my_ranking() -> dict:
    return {"rank": 18, "score": 842, "accuracy": 0.7, "solved_count": 100}
