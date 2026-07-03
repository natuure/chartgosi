import json

import pytest

from app.repositories.ai_reports import build_insufficient_summary
from app.services.openai_reports import extract_output_text, normalize_ai_report


def test_extract_output_text_from_responses_payload() -> None:
    payload = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(
                            {
                                "summary": "좋은 추세 판단입니다.",
                                "trait_scores": {
                                    "trend_reading": 80,
                                    "speed_control": 70,
                                    "consistency": 65,
                                },
                                "recommendations": [
                                    {
                                        "title": "컵앤핸들 훈련",
                                        "description": "눌림 구간을 반복해서 확인하세요.",
                                        "href": "/play?pattern=cup-and-handle",
                                    }
                                ],
                            },
                            ensure_ascii=False,
                        ),
                    }
                ],
            }
        ]
    }

    assert "좋은 추세 판단" in extract_output_text(payload)


def test_extract_output_text_raises_without_text() -> None:
    with pytest.raises(ValueError):
        extract_output_text({"output": []})


def test_normalize_ai_report_clamps_scores_and_rejects_external_href() -> None:
    report = normalize_ai_report(
        {
            "summary": "추세 추종 판단은 좋지만 속도 조절이 필요합니다.",
            "trait_scores": {
                "trend_reading": 120,
                "speed_control": -5,
                "consistency": 60,
            },
            "recommendations": [
                {
                    "title": "외부 링크 방지",
                    "description": "앱 내부 훈련으로 이동해야 합니다.",
                    "href": "https://example.com",
                }
            ],
        }
    )

    assert report["trait_scores"]["trend_reading"] == 100
    assert report["trait_scores"]["speed_control"] == 0
    assert report["recommendations"][0]["href"] == "/play"


def test_build_insufficient_summary_mentions_remaining_questions() -> None:
    assert "2문제를 더" in build_insufficient_summary(1)
