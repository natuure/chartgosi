import json
from typing import Any

import httpx

from app.core.config import settings

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"

REPORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {
            "type": "string",
            "description": "Korean learning feedback summary. Must not include investment advice.",
        },
        "trait_scores": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "trend_reading": {"type": "integer", "minimum": 0, "maximum": 100},
                "speed_control": {"type": "integer", "minimum": 0, "maximum": 100},
                "consistency": {"type": "integer", "minimum": 0, "maximum": 100},
            },
            "required": ["trend_reading", "speed_control", "consistency"],
        },
        "recommendations": {
            "type": "array",
            "minItems": 1,
            "maxItems": 3,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "href": {"type": "string"},
                },
                "required": ["title", "description", "href"],
            },
        },
    },
    "required": ["summary", "trait_scores", "recommendations"],
}

SYSTEM_PROMPT = """
You are ChartGosi's chart-learning coach.
Analyze quiz answer history only as educational feedback for chart-pattern practice.
Never provide investment advice, buy/sell recommendations, profit predictions, or real-market instructions.
Write concise Korean feedback that helps the learner understand pattern weaknesses, pacing, and next training actions.
Use only the JSON schema. Keep recommendation href values inside the app, such as /play, /patterns, or /play?pattern={slug}.
""".strip()


async def generate_openai_report(input_data: dict[str, Any]) -> dict[str, Any] | None:
    if not settings.openai_api_key.strip():
        return None

    request_body = {
        "model": settings.openai_model,
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(input_data, ensure_ascii=False, default=str),
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "chartgosi_ai_report",
                "strict": True,
                "schema": REPORT_SCHEMA,
            }
        },
        "max_output_tokens": 1200,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            OPENAI_RESPONSES_URL,
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json=request_body,
        )
        response.raise_for_status()

    return normalize_ai_report(json.loads(extract_output_text(response.json())))


def extract_output_text(response: dict[str, Any]) -> str:
    chunks: list[str] = []
    for output_item in response.get("output", []):
        if output_item.get("type") != "message":
            continue
        for content_item in output_item.get("content", []):
            if content_item.get("type") == "output_text" and isinstance(content_item.get("text"), str):
                chunks.append(content_item["text"])

    text = "".join(chunks).strip()
    if not text:
        raise ValueError("OpenAI response did not include output_text")
    return text


def normalize_ai_report(report: dict[str, Any]) -> dict[str, Any]:
    summary = str(report.get("summary", "")).strip()
    if not summary:
        raise ValueError("OpenAI report summary is empty")

    trait_scores = report.get("trait_scores")
    if not isinstance(trait_scores, dict):
        raise ValueError("OpenAI report trait_scores is invalid")

    recommendations = report.get("recommendations")
    if not isinstance(recommendations, list) or not recommendations:
        raise ValueError("OpenAI report recommendations is invalid")

    return {
        "summary": summary,
        "trait_scores": {
            "trend_reading": clamp_score(trait_scores.get("trend_reading")),
            "speed_control": clamp_score(trait_scores.get("speed_control")),
            "consistency": clamp_score(trait_scores.get("consistency")),
        },
        "recommendations": [
            {
                "title": str(item.get("title", "추천 훈련")).strip()[:80],
                "description": str(item.get("description", "다음 문제를 풀며 학습 기록을 쌓아보세요.")).strip()[:220],
                "href": normalize_href(item.get("href")),
            }
            for item in recommendations[:3]
            if isinstance(item, dict)
        ],
    }


def clamp_score(value: Any) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        score = 0
    return min(100, max(0, score))


def normalize_href(value: Any) -> str:
    href = str(value or "/play").strip()
    if not href.startswith("/") or href.startswith("//"):
        return "/play"
    return href[:120]
