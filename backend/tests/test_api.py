from fastapi.testclient import TestClient

from app.api.v1.routes import answers as answers_route
from app.api.v1.routes import patterns as patterns_route
from app.api.v1.routes import questions as questions_route
from app.api.v1.routes import rankings as rankings_route
from app.api.v1.routes import stats as stats_route
from app.api.v1.routes import wrong_notes as wrong_notes_route
from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_patterns(monkeypatch) -> None:
    async def fake_list_patterns(_session):
        return [
            {"id": str(index), "slug": f"pattern-{index}", "name": f"패턴 {index}", "question_count": index}
            for index in range(10)
        ]

    monkeypatch.setattr(patterns_route.patterns_repository, "list_patterns", fake_list_patterns)

    response = client.get("/api/v1/patterns")
    assert response.status_code == 200
    assert len(response.json()) == 10


def test_today_question_and_submit_answer(monkeypatch) -> None:
    async def fake_get_today_question(_session, pattern_slug=None):
        assert pattern_slug is None
        return {
            "id": "20000000-0000-0000-0000-000000000001",
            "pattern": {
                "id": "10000000-0000-0000-0000-000000000001",
                "slug": "cup-and-handle",
                "name": "컵앤핸들",
                "question_count": 1,
            },
            "difficulty": "medium",
            "difficulty_label": "중급",
            "market_regime": "sideways",
            "base_date": "2024-06-21",
            "chart_data": [],
            "hidden_candles_count": 5,
            "answer_options": ["up", "sideways", "down"],
            "public_accuracy": 0.7,
        }

    async def fake_submit_answer(_session, question_id, payload):
        return {
            "answer_id": "30000000-0000-0000-0000-000000000001",
            "question_id": question_id,
            "selected_answer": payload.selected_answer,
            "correct_answer": "up",
            "is_correct": payload.selected_answer == "up",
        }

    monkeypatch.setattr(questions_route.questions_repository, "get_today_question", fake_get_today_question)
    monkeypatch.setattr(questions_route.answers_repository, "submit_answer", fake_submit_answer)

    question_response = client.get("/api/v1/questions/today")
    assert question_response.status_code == 200
    question = question_response.json()
    assert "correct_answer" not in question
    assert "actual_next_candles" not in question

    answer_response = client.post(
        f"/api/v1/questions/{question['id']}/answers",
        json={
            "selected_answer": "up",
            "confidence": 70,
            "reason_tags": ["volume", "trend"],
            "answer_duration_ms": 18200,
            "is_retry": False,
        },
    )
    assert answer_response.status_code == 201
    assert answer_response.json()["is_correct"] is True


def test_today_question_by_pattern(monkeypatch) -> None:
    async def fake_get_today_question(_session, pattern_slug=None):
        assert pattern_slug == "cup-and-handle"
        return {
            "id": "20000000-0000-0000-0000-000000000001",
            "pattern": {
                "id": "10000000-0000-0000-0000-000000000001",
                "slug": "cup-and-handle",
                "name": "컵앤핸들",
                "question_count": 1,
            },
            "difficulty": "medium",
            "difficulty_label": "중급",
            "market_regime": "sideways",
            "base_date": "2024-06-21",
            "chart_data": [],
            "hidden_candles_count": 5,
            "answer_options": ["up", "sideways", "down"],
            "public_accuracy": 0.7,
        }

    monkeypatch.setattr(questions_route.questions_repository, "get_today_question", fake_get_today_question)

    response = client.get("/api/v1/questions/today?pattern_slug=cup-and-handle")
    assert response.status_code == 200
    assert response.json()["pattern"]["slug"] == "cup-and-handle"


def test_pattern_questions(monkeypatch) -> None:
    async def fake_list_pattern_questions(_session, pattern_key):
        assert pattern_key == "cup-and-handle"
        return [
            {
                "id": "20000000-0000-0000-0000-000000000001",
                "pattern": {
                    "id": "10000000-0000-0000-0000-000000000001",
                    "slug": "cup-and-handle",
                    "name": "컵앤핸들",
                    "question_count": 0,
                },
                "difficulty": "medium",
                "difficulty_label": "중급",
                "market_regime": "sideways",
                "base_date": "2024-06-21",
                "public_accuracy": 0.7,
                "total_answers": 2,
            }
        ]

    monkeypatch.setattr(patterns_route.questions_repository, "list_pattern_questions", fake_list_pattern_questions)

    response = client.get("/api/v1/patterns/cup-and-handle/questions")
    assert response.status_code == 200
    assert response.json()[0]["total_answers"] == 2


def test_answer_result(monkeypatch) -> None:
    async def fake_get_answer_result(_session, answer_id):
        return {
            "answer_id": answer_id,
            "question_id": "20000000-0000-0000-0000-000000000001",
            "pattern": {
                "id": "10000000-0000-0000-0000-000000000001",
                "slug": "cup-and-handle",
                "name": "컵앤핸들",
                "question_count": 0,
            },
            "selected_answer": "up",
            "correct_answer": "up",
            "is_correct": True,
            "actual_next_candles": [],
            "ai_explanation": "거래량 증가와 이동평균선 지지가 확인됩니다.",
            "choice_distribution": {"up": 1.0, "sideways": 0.0, "down": 0.0},
        }

    monkeypatch.setattr(answers_route.answers_repository, "get_answer_result", fake_get_answer_result)

    response = client.get("/api/v1/answers/30000000-0000-0000-0000-000000000001/result")
    assert response.status_code == 200
    assert response.json()["correct_answer"] == "up"


def test_mark_explanation_viewed(monkeypatch) -> None:
    async def fake_mark_explanation_viewed(_session, answer_id):
        assert answer_id == "30000000-0000-0000-0000-000000000001"
        return True

    monkeypatch.setattr(answers_route.answers_repository, "mark_explanation_viewed", fake_mark_explanation_viewed)

    response = client.patch("/api/v1/answers/30000000-0000-0000-0000-000000000001/explanation-viewed")
    assert response.status_code == 200
    assert response.json()["viewed_ai_explanation"] is True


def test_mark_explanation_viewed_not_found(monkeypatch) -> None:
    async def fake_mark_explanation_viewed(_session, _answer_id):
        return False

    monkeypatch.setattr(answers_route.answers_repository, "mark_explanation_viewed", fake_mark_explanation_viewed)

    response = client.patch("/api/v1/answers/30000000-0000-0000-0000-000000000404/explanation-viewed")
    assert response.status_code == 404


def test_wrong_notes(monkeypatch) -> None:
    async def fake_list_wrong_notes(_session, limit, offset):
        return {
            "items": [
                {
                    "answer_id": "30000000-0000-0000-0000-000000000002",
                    "question_id": "20000000-0000-0000-0000-000000000001",
                    "pattern": {
                        "id": "10000000-0000-0000-0000-000000000001",
                        "slug": "cup-and-handle",
                        "name": "컵앤핸들",
                        "question_count": 0,
                    },
                    "difficulty": "medium",
                    "difficulty_label": "중급",
                    "base_date": "2024-06-21",
                    "selected_answer": "down",
                    "correct_answer": "up",
                    "created_at": "2026-07-01 10:00:00+09",
                    "viewed_ai_explanation": False,
                    "ai_explanation": "돌파 구간에서 거래량 증가가 확인됩니다.",
                }
            ],
            "total": 1,
            "limit": limit,
            "offset": offset,
        }

    monkeypatch.setattr(wrong_notes_route.wrong_notes_repository, "list_wrong_notes", fake_list_wrong_notes)

    response = client.get("/api/v1/wrong-notes?limit=10&offset=0")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["limit"] == 10
    assert body["items"][0]["selected_answer"] == "down"
    assert body["items"][0]["correct_answer"] == "up"


def test_wrong_note_detail(monkeypatch) -> None:
    async def fake_get_wrong_note(_session, answer_id):
        return {
            "answer_id": answer_id,
            "question_id": "20000000-0000-0000-0000-000000000001",
            "pattern": {
                "id": "10000000-0000-0000-0000-000000000001",
                "slug": "cup-and-handle",
                "name": "컵앤핸들",
                "question_count": 0,
            },
            "difficulty": "medium",
            "difficulty_label": "중급",
            "base_date": "2024-06-21",
            "selected_answer": "down",
            "correct_answer": "up",
            "created_at": "2026-07-01 10:00:00+09",
            "viewed_ai_explanation": True,
            "ai_explanation": "돌파 구간에서 거래량 증가가 확인됩니다.",
            "actual_next_candles": [],
        }

    monkeypatch.setattr(wrong_notes_route.wrong_notes_repository, "get_wrong_note", fake_get_wrong_note)

    response = client.get("/api/v1/wrong-notes/30000000-0000-0000-0000-000000000002")
    assert response.status_code == 200
    assert response.json()["actual_next_candles"] == []


def test_wrong_note_detail_not_found(monkeypatch) -> None:
    async def fake_get_wrong_note(_session, _answer_id):
        return None

    monkeypatch.setattr(wrong_notes_route.wrong_notes_repository, "get_wrong_note", fake_get_wrong_note)

    response = client.get("/api/v1/wrong-notes/30000000-0000-0000-0000-000000000003")
    assert response.status_code == 404


def test_my_stats(monkeypatch) -> None:
    async def fake_get_my_stats(_session):
        return {
            "solved_count": 3,
            "correct_count": 2,
            "wrong_count": 1,
            "accuracy": 0.6667,
            "average_duration_ms": 15000,
            "pattern_stats": [
                {
                    "pattern": {
                        "id": "10000000-0000-0000-0000-000000000001",
                        "slug": "cup-and-handle",
                        "name": "컵앤핸들",
                        "question_count": 0,
                    },
                    "solved_count": 3,
                    "correct_count": 2,
                    "accuracy": 0.6667,
                }
            ],
        }

    monkeypatch.setattr(stats_route.stats_repository, "get_my_stats", fake_get_my_stats)

    response = client.get("/api/v1/stats/me")
    assert response.status_code == 200
    body = response.json()
    assert body["solved_count"] == 3
    assert body["wrong_count"] == 1
    assert body["pattern_stats"][0]["pattern"]["slug"] == "cup-and-handle"


def test_rankings(monkeypatch) -> None:
    async def fake_list_rankings(_session, period_type, limit):
        return {
            "period_type": period_type,
            "items": [
                {
                    "rank": 1,
                    "user_id": "00000000-0000-0000-0000-000000000001",
                    "nickname": "ChartGosi Dev",
                    "score": 26,
                    "accuracy": 0.6667,
                    "solved_count": 3,
                    "correct_count": 2,
                }
            ],
        }

    monkeypatch.setattr(rankings_route.rankings_repository, "list_rankings", fake_list_rankings)

    response = client.get("/api/v1/rankings?period_type=weekly&limit=10")
    assert response.status_code == 200
    body = response.json()
    assert body["period_type"] == "weekly"
    assert body["items"][0]["score"] == 26


def test_my_ranking(monkeypatch) -> None:
    async def fake_get_my_ranking(_session, period_type):
        return {
            "period_type": period_type,
            "rank": 1,
            "user_id": "00000000-0000-0000-0000-000000000001",
            "nickname": "ChartGosi Dev",
            "score": 26,
            "accuracy": 0.6667,
            "solved_count": 3,
            "correct_count": 2,
        }

    monkeypatch.setattr(rankings_route.rankings_repository, "get_my_ranking", fake_get_my_ranking)

    response = client.get("/api/v1/rankings/me?period_type=weekly")
    assert response.status_code == 200
    assert response.json()["rank"] == 1
