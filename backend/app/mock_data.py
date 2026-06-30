PATTERNS = [
    {"id": "p_cup_handle", "slug": "cup-and-handle", "name": "컵앤핸들", "question_count": 125},
    {"id": "p_double_bottom", "slug": "double-bottom", "name": "W바닥", "question_count": 118},
    {"id": "p_box_breakout", "slug": "box-breakout", "name": "박스권 돌파", "question_count": 132},
    {"id": "p_new_high_breakout", "slug": "new-high-breakout", "name": "신고가 돌파", "question_count": 110},
    {"id": "p_pullback", "slug": "pullback", "name": "눌림목", "question_count": 115},
    {"id": "p_triangle", "slug": "triangle", "name": "삼각수렴", "question_count": 103},
    {"id": "p_flag", "slug": "flag", "name": "플래그", "question_count": 96},
    {"id": "p_inverse_head_shoulders", "slug": "inverse-head-shoulders", "name": "역헤드앤숄더", "question_count": 99},
    {"id": "p_ma_breakout", "slug": "moving-average-breakout", "name": "이동평균선 돌파", "question_count": 108},
    {"id": "p_volume_spike", "slug": "volume-spike", "name": "거래량 급증", "question_count": 124},
]


def _candle(index: int) -> dict:
    open_price = 92 + (index * 0.18) + ((index % 7) - 3) * 0.75
    close_price = open_price + ((index % 5) - 2) * 0.9
    return {
        "time": f"2024-05-{(index % 28) + 1:02d}",
        "open": round(open_price, 2),
        "high": round(max(open_price, close_price) + 1.5, 2),
        "low": round(min(open_price, close_price) - 1.4, 2),
        "close": round(close_price, 2),
        "volume": 800000 + ((index * 137000) % 1200000),
        "ma20": round(94 + (index * 0.16), 2),
    }


SAMPLE_QUESTION = {
    "id": "q_sample_001",
    "pattern": PATTERNS[0],
    "difficulty": "medium",
    "market_regime": "sideways",
    "base_date": "2024-06-21",
    "chart_data": [_candle(index) for index in range(56)],
    "hidden_candles_count": 5,
    "answer_options": ["up", "sideways", "down"],
    "correct_answer": "up",
    "public_accuracy": 0.7,
    "ai_explanation": "컵앤핸들 구간 이후 거래량이 회복되고 이동평균선 위에서 지지되는 흐름입니다.",
}

RESULT = {
    "is_correct": True,
    "correct_answer": "up",
    "actual_next_candles": [_candle(index) for index in range(56, 61)],
    "ai_explanation": SAMPLE_QUESTION["ai_explanation"],
    "choice_distribution": {"up": 0.62, "sideways": 0.25, "down": 0.13},
}
