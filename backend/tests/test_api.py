from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_patterns() -> None:
    response = client.get("/api/v1/patterns")
    assert response.status_code == 200
    assert len(response.json()) == 10


def test_today_question_and_submit_answer() -> None:
    question_response = client.get("/api/v1/questions/today")
    assert question_response.status_code == 200
    question = question_response.json()

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


def test_answer_result() -> None:
    response = client.get("/api/v1/answers/a_mock_001/result")
    assert response.status_code == 200
    assert response.json()["correct_answer"] == "up"
