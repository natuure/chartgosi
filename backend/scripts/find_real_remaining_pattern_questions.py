import json
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable


ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_JSON = ROOT_DIR / "data" / "real_remaining_pattern_candidates.json"
SCORECARD_SQL = ROOT_DIR / "db" / "seeds" / "remaining_pattern_scorecards.sql"
SEED_DIR = ROOT_DIR / "db" / "seeds"
NAVER_MARKET_URL = "https://finance.naver.com/sise/sise_market_sum.naver"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

NEXT_FIVE_UP_THRESHOLD = 0.10
NEXT_FIVE_DOWN_THRESHOLD = -0.10
TARGET_ANSWER_COUNTS = {"up": 5, "sideways": 2, "down": 3}
QUESTION_ANSWER_ORDER = ["up", "down", "up", "sideways", "up", "down", "up", "sideways", "up", "down"]
PAGES_PER_MARKET = 8
MAX_WORKERS = 16
MIN_SCORE = 75

PATTERN_ORDER = [
    "pullback",
    "triangle",
    "flag",
    "inverse-head-shoulders",
    "moving-average-breakout",
    "volume-spike",
]

PATTERN_META = {
    "pullback": {
        "name": "눌림목",
        "file": "real_pullback_questions.sql",
        "uuid_prefix": "27000000",
        "market_regime": "bull",
        "timeframe": "1d",
        "description": "상승 추세, 짧은 조정, 지지선 반등, 거래량 감소/회복을 기준으로 선별했습니다.",
    },
    "triangle": {
        "name": "변동성축소",
        "file": "real_triangle_questions.sql",
        "uuid_prefix": "28000000",
        "market_regime": "sideways",
        "timeframe": "1wk",
        "description": "마크 미너비니의 VCP 관점으로, 주봉에서 수축폭과 거래량이 단계적으로 줄어드는 구조를 기준으로 선별합니다.",
    },
    "flag": {
        "name": "플래그",
        "file": "real_flag_questions.sql",
        "uuid_prefix": "29000000",
        "market_regime": "bull",
        "timeframe": "1d",
        "description": "강한 상승 기둥, 짧은 조정 채널, 조정 거래량 감소, 채널 상단 재돌파를 기준으로 선별했습니다.",
    },
    "inverse-head-shoulders": {
        "name": "역헤드앤숄더",
        "file": "real_inverse_head_shoulders_questions.sql",
        "uuid_prefix": "30000000",
        "market_regime": "bear",
        "timeframe": "1d",
        "description": "왼쪽 어깨, 더 깊은 머리, 높아진 오른쪽 어깨, neckline 돌파를 기준으로 선별했습니다.",
    },
    "moving-average-breakout": {
        "name": "이동평균선 돌파",
        "file": "real_moving_average_breakout_questions.sql",
        "uuid_prefix": "31000000",
        "market_regime": "sideways",
        "timeframe": "1d",
        "description": "주요 이동평균선 아래 눌림 이후 종가 회복, 단기선 기울기 개선, 거래량 회복을 기준으로 선별했습니다.",
    },
    "volume-spike": {
        "name": "거래량 급증",
        "file": "real_volume_spike_questions.sql",
        "uuid_prefix": "32000000",
        "market_regime": "sideways",
        "timeframe": "1d",
        "description": "최근 평균 대비 거래량 급증, 종가 위치, 가격 변화, 주요 가격대 돌파/지지를 기준으로 선별했습니다.",
    },
}

SCORECARDS = {
    "pullback": {
        "max_score": 90,
        "primary_threshold": 75,
        "high_confidence_threshold": 85,
        "criteria": [
            {"key": "trend_strength", "label": "선행 상승 추세", "max_points": 20, "description": "최근 25거래일 저점 대비 30% 이상 상승하면 20점입니다."},
            {"key": "ma_distance", "label": "이동평균선 이격도", "max_points": 25, "description": "조정 구간 저점 또는 조정확정일 종가가 5/10/20/60일선 중 하나와 플러스마이너스 2% 이내에 있습니다."},
            {"key": "pullback_duration", "label": "조정 기간", "max_points": 10, "description": "확정봉 기준 최근 20거래일 안에서 가장 높은 종가 봉 다음 봉부터 확정봉까지를 조정 구간으로 보며, 20거래일 이하만 허용합니다."},
            {"key": "lower_wick", "label": "아래꼬리 확인", "max_points": 15, "description": "조정확정일 봉의 아래꼬리 비율이 35% 이상이어야 합니다. 양봉은 시가-저가, 음봉은 종가-저가를 전체 봉 길이로 나눕니다."},
            {"key": "volume_dry_up", "label": "조정 거래량 감소", "max_points": 15, "description": "조정 구간 평균 거래량이 선행 상승 구간보다 줄어듭니다."},
            {"key": "ma_structure", "label": "이동평균선 구조", "max_points": 5, "description": "단기 이동평균선이 중기 이동평균선 위에 있거나 상승 중입니다."},
        ],
    },
    "triangle": {
        "max_score": 100,
        "primary_threshold": 75,
        "high_confidence_threshold": 85,
        "criteria": [
            {"key": "prior_uptrend", "label": "선행 상승 추세", "max_points": 15, "description": "1차 국소 고점 전 2~5주 주봉 종가 기준 상승률이 30% 이상이어야 합니다."},
            {"key": "contraction_count", "label": "수축 횟수", "max_points": 15, "description": "종가 기준 수축 구간이 최소 2회, 최대 5회 확인되어야 합니다."},
            {"key": "contraction_depths", "label": "수축폭 감소", "max_points": 25, "description": "뒤로 갈수록 각 수축의 낙폭이 작아져야 합니다."},
            {"key": "volume_dry_up", "label": "거래량 감소", "max_points": 15, "description": "수축이 진행될수록 거래량이 줄어드는 구조를 평가합니다."},
            {"key": "last_contraction_quality", "label": "마지막 수축 품질", "max_points": 15, "description": "마지막 수축이 좁고 짧으며 매물 압력이 작을수록 점수가 높습니다."},
            {"key": "ma_structure", "label": "이동평균선 구조", "max_points": 10, "description": "주봉 MA10/30/40이 상승 추세 또는 정배열에 가까운지 평가합니다."},
            {"key": "pivot_readiness", "label": "피벗 돌파", "max_points": 5, "description": "국소 고점들을 직선으로 이은 피벗선을 마지막 봉 종가가 돌파했는지 평가합니다."},
        ],
    },
    "flag": {
        "max_score": 100,
        "primary_threshold": 75,
        "high_confidence_threshold": 85,
        "criteria": [
            {"key": "pole_strength", "label": "상승 기둥 강도", "max_points": 20, "description": "5~15거래일 안에 20% 이상 급등이 먼저 나옵니다."},
            {"key": "flag_duration", "label": "플래그 기간", "max_points": 10, "description": "조정 채널은 5~20거래일로 짧게 형성됩니다."},
            {"key": "retracement_control", "label": "되돌림 제한", "max_points": 20, "description": "조정폭이 상승 기둥의 50% 이내로 제한됩니다."},
            {"key": "channel_slope", "label": "반대 방향 조정", "max_points": 15, "description": "조정 구간 고점과 저점이 완만하게 낮아집니다."},
            {"key": "volume_dry_up", "label": "조정 거래량 감소", "max_points": 15, "description": "조정 구간 거래량이 상승 기둥보다 감소합니다."},
            {"key": "breakout_strength", "label": "채널 상단 돌파", "max_points": 15, "description": "마지막 봉 종가가 조정 채널 상단을 2% 이상 돌파합니다."},
            {"key": "ma_support", "label": "50일선 위 유지", "max_points": 5, "description": "패턴 종료 봉이 50일선 위에 있습니다."},
        ],
    },
    "inverse-head-shoulders": {
        "max_score": 100,
        "primary_threshold": 75,
        "high_confidence_threshold": 85,
        "criteria": [
            {"key": "prior_downtrend", "label": "선행 하락", "max_points": 15, "description": "패턴 전 40거래일 안에 15% 이상 하락이 먼저 나옵니다."},
            {"key": "head_depth", "label": "머리 저점 깊이", "max_points": 20, "description": "가운데 저점이 양쪽 어깨보다 5% 이상 낮습니다."},
            {"key": "shoulder_balance", "label": "양쪽 어깨 균형", "max_points": 15, "description": "오른쪽 어깨와 왼쪽 어깨 종가 비율이 90~110% 범위에 있습니다."},
            {"key": "right_shoulder_strength", "label": "오른쪽 어깨 방어", "max_points": 15, "description": "오른쪽 어깨가 머리 저점을 재이탈하지 않습니다."},
            {"key": "neckline_breakout", "label": "neckline 돌파", "max_points": 20, "description": "마지막 봉 종가가 neckline을 2% 이상 돌파합니다."},
            {"key": "volume_recovery", "label": "돌파 거래량 회복", "max_points": 10, "description": "돌파 봉 거래량이 최근 20일 평균 이상입니다."},
            {"key": "ma_recovery", "label": "50일선 회복", "max_points": 5, "description": "돌파 봉 종가가 50일선 위에 있습니다."},
        ],
    },
    "moving-average-breakout": {
        "max_score": 100,
        "primary_threshold": 75,
        "high_confidence_threshold": 85,
        "criteria": [
            {"key": "prior_below_ma", "label": "이전 이평선 하회", "max_points": 15, "description": "최근 20거래일 동안 주요 이동평균선 아래에 머문 기간이 충분합니다."},
            {"key": "breakout_ma_level", "label": "돌파 이평선 중요도", "max_points": 20, "description": "50일선, 150일선, 200일선 중 더 장기선을 회복할수록 점수가 높습니다."},
            {"key": "close_strength", "label": "종가 돌파 강도", "max_points": 15, "description": "종가가 기준 이동평균선보다 2% 이상 위에서 마감합니다."},
            {"key": "ma_slope_improvement", "label": "이평선 기울기 개선", "max_points": 15, "description": "50일선 하락세가 완화되거나 상승 전환합니다."},
            {"key": "volume_confirmation", "label": "거래량 확인", "max_points": 15, "description": "돌파 봉 거래량이 최근 20일 평균 이상입니다."},
            {"key": "body_quality", "label": "캔들 몸통 품질", "max_points": 10, "description": "돌파 봉이 양봉이며 종가가 고가 근처에 있습니다."},
            {"key": "overheat_control", "label": "단기 과열 제한", "max_points": 10, "description": "돌파 직전 10거래일 급등이 과도하지 않습니다."},
        ],
    },
    "volume-spike": {
        "max_score": 100,
        "primary_threshold": 75,
        "high_confidence_threshold": 85,
        "criteria": [
            {"key": "volume_ratio", "label": "거래량 배율", "max_points": 25, "description": "거래량이 최근 20일 평균 대비 200/300/500% 이상으로 증가합니다."},
            {"key": "price_response", "label": "가격 반응", "max_points": 20, "description": "거래량 급증 봉 종가가 전일 대비 5% 이상 상승하거나 주요 가격대를 회복합니다."},
            {"key": "close_quality", "label": "종가 위치 품질", "max_points": 15, "description": "종가가 고가 근처에 있고 윗꼬리가 과도하지 않습니다."},
            {"key": "breakout_context", "label": "가격대 돌파 맥락", "max_points": 15, "description": "최근 20거래일 고점 또는 50일선을 함께 돌파하면 점수가 높습니다."},
            {"key": "base_context", "label": "이전 눌림/횡보", "max_points": 10, "description": "급증 전 10~30거래일 동안 과열보다 준비 구간이 존재합니다."},
            {"key": "ma_recovery", "label": "이동평균선 회복", "max_points": 10, "description": "거래량 급증 봉 종가가 50일선 위에 있습니다."},
            {"key": "risk_control", "label": "꼬리/갭 리스크 제한", "max_points": 5, "description": "긴 윗꼬리와 과도한 갭 상승을 감점합니다."},
        ],
    },
}

SCORECARDS["triangle"]["criteria"] = [
    {"key": "prior_uptrend", "label": "선행 상승 추세", "max_points": 15, "description": "1차 국소 고점 전 2~5주 주봉 종가 기준 상승률이 30% 이상이어야 합니다."},
    {"key": "contraction_count", "label": "수축 횟수", "max_points": 15, "description": "종가 기준 수축 구간이 최소 2회, 최대 5회 확인되어야 합니다."},
    {"key": "contraction_depths", "label": "수축폭 감소", "max_points": 25, "description": "1차 -45%, 2차 -33%, 3차 -25%, 4차 -15%, 5차 -8% 한도 안에서 뒤로 갈수록 수축폭이 작아져야 합니다."},
    {"key": "volume_dry_up", "label": "거래량 감소", "max_points": 15, "description": "수축 횟수가 반복될수록 각 수축 구간의 평균 거래량이 같거나 줄어야 합니다."},
    {"key": "last_contraction_quality", "label": "마지막 수축 품질", "max_points": 15, "description": "마지막 수축은 좁고 짧을수록 좋으며, 5차 수축은 최대 -8%까지만 허용합니다."},
    {"key": "ma_structure", "label": "이동평균선 구조", "max_points": 10, "description": "주봉 MA10/30/40이 상승 추세 또는 정배열에 가까운지 평가합니다."},
    {"key": "pivot_readiness", "label": "피벗 돌파", "max_points": 5, "description": "국소 고점들을 직선으로 이은 피벗선을 마지막 봉 종가가 돌파했는지 평가합니다."},
]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")


@dataclass(frozen=True)
class ListedStock:
    code: str
    name: str
    market: str
    yahoo_symbol: str


def main() -> None:
    write_scorecard_sql()
    target_slugs = [slug for slug in sys.argv[1:] if slug in PATTERN_ORDER] or PATTERN_ORDER
    stocks = load_listed_stocks(PAGES_PER_MARKET)
    print(f"listed_candidates={len(stocks)}", flush=True)
    print(f"target_patterns={','.join(target_slugs)}", flush=True)

    scored: dict[str, list[dict[str, Any]]] = {slug: [] for slug in target_slugs}
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    futures = {}
    try:
        futures = {executor.submit(scan_stock, stock): stock for stock in stocks}
        for index, future in enumerate(as_completed(futures), start=1):
            stock = futures[future]
            try:
                results = future.result()
                for slug, items in results.items():
                    if slug not in scored:
                        continue
                    if items:
                        scored[slug].extend(items)
                summary_parts = [
                    f"{slug}:{len(items)}"
                    for slug, items in results.items()
                    if slug in scored
                    if items
                ]
                if summary_parts:
                    print(f"pass {stock.code} {stock.name} {' '.join(summary_parts)}", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"skip {stock.code} {stock.name}: {exc}", flush=True)
            if index % 100 == 0:
                counts = ", ".join(f"{slug}={len(items)}" for slug, items in scored.items())
                print(f"scanned={index} {counts}", flush=True)
            if all(has_balanced_questions(items) for items in scored.values()):
                print(f"balanced_candidates_ready_at={index}", flush=True)
                break
    finally:
        for future in futures:
            future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)

    selected_by_slug: dict[str, list[dict[str, Any]]] = {}
    for slug in target_slugs:
        selected = select_balanced_questions(scored[slug])
        selected_by_slug[slug] = selected
        counts = {answer: sum(1 for item in selected if item["correct_answer"] == answer) for answer in TARGET_ANSWER_COUNTS}
        print(f"{slug}_selected_counts={counts}", flush=True)
        write_question_sql(slug, selected)

    OUTPUT_JSON.parent.mkdir(exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(selected_by_slug, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote_json={OUTPUT_JSON}", flush=True)


def load_listed_stocks(pages_per_market: int) -> list[ListedStock]:
    stocks: list[ListedStock] = []
    seen: set[str] = set()
    for sosok, market, suffix in ((0, "KOSPI", "KS"), (1, "KOSDAQ", "KQ")):
        for page in range(1, pages_per_market + 1):
            url = f"{NAVER_MARKET_URL}?{urllib.parse.urlencode({'sosok': sosok, 'page': page})}"
            html = fetch_text(url, encoding="euc-kr")
            matches = re.findall(r'<a href="/item/main\.naver\?code=(\d{6})"[^>]*>(.*?)</a>', html)
            if not matches:
                break
            for code, raw_name in matches:
                if code in seen:
                    continue
                name = clean_html(raw_name)
                if is_fund_or_note(name):
                    continue
                seen.add(code)
                stocks.append(ListedStock(code=code, name=name, market=market, yahoo_symbol=f"{code}.{suffix}"))
            time.sleep(0.08)
    return stocks


def is_fund_or_note(name: str) -> bool:
    keywords = ("KODEX", "TIGER", "ACE", "RISE", "SOL ", "PLUS", "TIME", "UNICORN", "KOSEF", "KBSTAR", "HANARO", "ARIRANG", "ETF", "ETN", "스팩", "SPAC")
    return any(keyword in name for keyword in keywords)


def fetch_text(url: str, encoding: str = "utf-8") -> str:
    request = urllib.request.Request(url, headers=REQUEST_HEADERS)
    with urllib.request.urlopen(request, timeout=12) as response:  # noqa: S310
        return response.read().decode(encoding, errors="ignore")


def fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=REQUEST_HEADERS)
    with urllib.request.urlopen(request, timeout=12) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def clean_html(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value).strip()


def fetch_daily_candles(symbol: str) -> list[dict[str, Any]]:
    period2 = int(datetime.now(UTC).timestamp())
    period1 = int((datetime.now(UTC) - timedelta(days=365 * 4)).timestamp())
    query = urllib.parse.urlencode({"period1": period1, "period2": period2, "interval": "1d", "events": "history", "includeAdjustedClose": "true"})
    return fetch_price_candles(symbol, query)


def fetch_weekly_candles(symbol: str) -> list[dict[str, Any]]:
    period2 = int(datetime.now(UTC).timestamp())
    period1 = int((datetime.now(UTC) - timedelta(days=365 * 6)).timestamp())
    query = urllib.parse.urlencode({"period1": period1, "period2": period2, "interval": "1wk", "events": "history", "includeAdjustedClose": "true"})
    return fetch_price_candles(symbol, query)


def fetch_price_candles(symbol: str, query: str) -> list[dict[str, Any]]:
    payload = fetch_json(f"{YAHOO_CHART_URL.format(symbol=urllib.parse.quote(symbol))}?{query}")
    result = payload.get("chart", {}).get("result") or []
    if not result:
        return []
    item = result[0]
    timestamps = item.get("timestamp") or []
    quote = ((item.get("indicators") or {}).get("quote") or [{}])[0]
    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []
    candles: list[dict[str, Any]] = []
    for index, timestamp in enumerate(timestamps):
        values = [opens, highs, lows, closes, volumes]
        if any(index >= len(series) or series[index] is None for series in values):
            continue
        candles.append(
            {
                "time": datetime.fromtimestamp(timestamp, UTC).date().isoformat(),
                "open": round(float(opens[index]), 2),
                "high": round(float(highs[index]), 2),
                "low": round(float(lows[index]), 2),
                "close": round(float(closes[index]), 2),
                "volume": int(volumes[index]),
                "ma5": 0,
                "ma10": 0,
                "ma20": 0,
                "ma30": 0,
                "ma40": 0,
                "ma50": 0,
                "ma60": 0,
                "ma150": 0,
                "ma200": 0,
            }
        )
    closes_for_ma: list[float] = []
    volumes_for_ma: list[int] = []
    for candle in candles:
        closes_for_ma.append(candle["close"])
        volumes_for_ma.append(candle["volume"])
        for period in (5, 10, 20, 30, 40, 50, 60, 150, 200):
            lookback = closes_for_ma[-period:]
            candle[f"ma{period}"] = round(sum(lookback) / len(lookback), 2)
        volume_lookback = volumes_for_ma[-20:]
        candle["volume_ma20"] = round(sum(volume_lookback) / len(volume_lookback), 2)
    return candles


def scan_stock(stock: ListedStock) -> dict[str, list[dict[str, Any]]]:
    daily_candles = fetch_daily_candles(stock.yahoo_symbol)
    weekly_candles = fetch_weekly_candles(stock.yahoo_symbol)
    if len(daily_candles) < 260 and len(weekly_candles) < 80:
        return {slug: [] for slug in PATTERN_ORDER}

    daily_evaluators: dict[str, Callable[[list[dict[str, Any]], int], dict[str, Any] | None]] = {
        "pullback": evaluate_pullback,
        "flag": evaluate_flag,
        "inverse-head-shoulders": evaluate_inverse_head_shoulders,
        "moving-average-breakout": evaluate_moving_average_breakout,
        "volume-spike": evaluate_volume_spike,
    }
    best: dict[str, dict[str, dict[str, Any]]] = {slug: {} for slug in PATTERN_ORDER}

    scan_candle_series(stock, daily_candles, daily_evaluators, best)
    scan_candle_series(stock, weekly_candles, {"triangle": evaluate_triangle}, best, min_index=60)
    return {slug: list(items.values()) for slug, items in best.items()}


def scan_candle_series(
    stock: ListedStock,
    candles: list[dict[str, Any]],
    evaluators: dict[str, Callable[[list[dict[str, Any]], int], dict[str, Any] | None]],
    best: dict[str, dict[str, dict[str, Any]]],
    min_index: int = 80,
) -> None:
    if len(candles) < min_index + 6:
        return
    for index in range(min_index, len(candles) - 5):
        for slug, evaluator in evaluators.items():
            score_result = evaluator(candles, index)
            if score_result is None or score_result["score"] < MIN_SCORE:
                continue
            start = max(0, score_result["indices"].get("start", index - 80))
            visible = candles[start : index + 1]
            future = candles[index + 1 : index + 6]
            if len(visible) < 15 or len(future) < 5:
                continue
            answer = classify_next_five(visible[-1], future)
            next_five_return = future[-1]["close"] / visible[-1]["close"] - 1
            result = {
                "stock": stock.__dict__,
                "score": round(score_result["score"], 2),
                "breakdown": score_result["breakdown"],
                "evidence": score_result["evidence"],
                "base_date": visible[-1]["time"],
                "chart_data": visible,
                "actual_next_candles": future,
                "correct_answer": answer,
                "next_five_return": round(next_five_return, 4),
            }
            current = best[slug].get(answer)
            if current is None or (result["score"], result["base_date"]) > (current["score"], current["base_date"]):
                best[slug][answer] = result


def evaluate_pullback(c: list[dict[str, Any]], i: int) -> dict[str, Any] | None:
    recent_high_start = max(0, i - 19)
    recent_high_window = c[recent_high_start : i + 1]
    if len(recent_high_window) < 5:
        return None
    high_offset = max(range(len(recent_high_window)), key=lambda index: recent_high_window[index]["close"])
    high_index = recent_high_start + high_offset
    pullback_start = high_index + 1
    if pullback_start > i:
        return None
    pullback_days = i - pullback_start + 1
    if pullback_days > 20:
        return None

    trend_start = max(0, i - 32)
    trend_window = c[max(0, i - 25) : i + 1]
    prior = c[trend_start:pullback_start]
    pb = c[pullback_start : i + 1]
    if len(trend_window) < 25 or len(prior) < 18 or len(pb) < pullback_days:
        return None
    recent_low = min(x["low"] for x in trend_window)
    recent_high = max(x["close"] for x in trend_window)
    trend_start_index = trend_start + min(range(len(prior)), key=lambda index: prior[index]["low"])
    trend_gain = recent_high / recent_low - 1
    if trend_gain < 0.25:
        return None
    pb_low = min(x["low"] for x in pb)
    pullback_depth = recent_high / pb_low - 1
    if pullback_depth < 0.03 or pullback_depth > 0.25:
        return None
    last = c[i]
    pb_low_candle = min(pb, key=lambda candle: candle["low"])
    close_ma_distances = {
        "ma5": abs(last["close"] / max(1, last["ma5"]) - 1),
        "ma10": abs(last["close"] / max(1, last["ma10"]) - 1),
        "ma20": abs(last["close"] / max(1, last["ma20"]) - 1),
        "ma60": abs(last["close"] / max(1, last["ma60"]) - 1),
    }
    low_ma_distances = {
        "ma5": abs(pb_low_candle["low"] / max(1, pb_low_candle["ma5"]) - 1),
        "ma10": abs(pb_low_candle["low"] / max(1, pb_low_candle["ma10"]) - 1),
        "ma20": abs(pb_low_candle["low"] / max(1, pb_low_candle["ma20"]) - 1),
        "ma60": abs(pb_low_candle["low"] / max(1, pb_low_candle["ma60"]) - 1),
    }
    close_support_ma, close_support_gap = min(close_ma_distances.items(), key=lambda item: item[1])
    low_support_ma, low_support_gap = min(low_ma_distances.items(), key=lambda item: item[1])
    if close_support_gap <= low_support_gap:
        support_basis = "확정봉 종가"
        support_ma = close_support_ma
        support_gap = close_support_gap
    else:
        support_basis = "조정 구간 저점"
        support_ma = low_support_ma
        support_gap = low_support_gap
    if support_gap > 0.02:
        return None
    lower_wick = lower_wick_ratio(last)
    if lower_wick < 0.35:
        return None
    prior_volume = avg(x["volume"] for x in prior[-15:])
    pb_volume = avg(x["volume"] for x in pb[:-1])
    volume_ratio = pb_volume / max(1, prior_volume)
    ma_touch_count = sum(1 for distance in close_ma_distances.values() if distance <= 0.02) + sum(
        1 for distance in low_ma_distances.values() if distance <= 0.02
    )
    breakdown = {
        "trend_strength": 20 if trend_gain >= 0.30 else 14,
        "ma_distance": 25 if support_gap <= 0.01 and ma_touch_count >= 2 else 20 if support_gap <= 0.01 else 15,
        "pullback_duration": 10 if 3 <= pullback_days <= 10 else 7,
        "lower_wick": 15 if lower_wick >= 0.50 else 10,
        "volume_dry_up": 15 if volume_ratio <= 0.75 else 10 if volume_ratio <= 0.95 else 5,
        "ma_structure": 5 if last["ma5"] >= last["ma20"] or last["ma10"] >= last["ma60"] else 0,
    }
    evidence = [
        f"최근 25일 저점 대비 상승률 {trend_gain * 100:.1f}%",
        f"눌림 낙폭 {pullback_depth * 100:.1f}%",
        f"조정 {pullback_days}거래일",
        f"조정 시작 {c[pullback_start]['time']} / 최근 20일 최고 종가 봉 {c[high_index]['time']}",
        f"{support_basis} {support_ma.upper()} 이격도 {support_gap * 100:.1f}%",
        f"±2% 이내 이동평균선 {ma_touch_count}개",
        f"아래꼬리 비율 {lower_wick * 100:.1f}%",
        f"조정 거래량/상승 거래량 {volume_ratio * 100:.1f}%",
    ]
    return score_result(breakdown, evidence, {"start": trend_start_index})



def evaluate_triangle(c: list[dict[str, Any]], i: int) -> dict[str, Any] | None:
    weeks = 50
    start = i - weeks + 1
    if start < 5:
        return None
    last = c[i]

    first_peak = find_vcp_first_peak(c, start, i)
    if not first_peak:
        return None
    first_peak_index, prior_gain, prior_gain_weeks = first_peak

    contractions = find_vcp_contractions(c, first_peak_index, i)
    if len(contractions) < 2 or len(contractions) > 5:
        return None

    depths = [item["depth"] for item in contractions]
    max_allowed_depths = [0.45, 0.33, 0.25, 0.15, 0.08]
    if any(depth > max_allowed_depths[index] for index, depth in enumerate(depths)):
        return None
    if any(depths[index + 1] - depths[index] >= 0.05 for index in range(len(depths) - 1)):
        return None

    trough_closes = [item["trough_close"] for item in contractions]
    if any(trough_closes[index] < trough_closes[index - 1] * 0.90 for index in range(1, len(trough_closes))):
        return None

    avg_volumes = [item["avg_volume"] for item in contractions]
    if any(avg_volumes[index + 1] > avg_volumes[index] for index in range(len(avg_volumes) - 1)):
        return None

    peak_indices = [item["peak_index"] for item in contractions]
    pivot = vcp_pivot_price(c, peak_indices, i)
    if pivot is None:
        return None
    pivot_breakout = last["close"] / max(1, pivot) - 1
    if pivot_breakout < 0 or pivot_breakout > 0.08:
        return None

    ma_bullish = last["ma10"] >= last["ma30"] >= last["ma40"]
    ma_rising = last["ma10"] >= c[i - 4]["ma10"] and last["ma30"] >= c[i - 8]["ma30"]
    if last["close"] < last["ma40"] * 0.97:
        return None

    last_contraction = contractions[-1]
    last_depth = last_contraction["depth"]
    depths_decreasing = sum(1 for index in range(len(depths) - 1) if depths[index + 1] <= depths[index])
    last_volume_ratio = avg_volumes[-1] / max(1, avg_volumes[0])

    breakdown = {
        "prior_uptrend": 15 if prior_gain >= 0.45 else 10,
        "contraction_count": 15 if len(contractions) >= 3 else 10,
        "contraction_depths": 25 if depths_decreasing == len(depths) - 1 and depths[-1] <= depths[0] * 0.65 else 18,
        "volume_dry_up": 15 if last_volume_ratio <= 0.75 else 10 if last_volume_ratio <= 0.90 else 5,
        "last_contraction_quality": 15 if last_depth <= 0.08 and last_contraction["duration"] <= 6 else 10,
        "ma_structure": 10 if ma_bullish else 6 if ma_rising else 0,
        "pivot_readiness": 5 if 0 <= pivot_breakout <= 0.03 else 3,
    }
    evidence = [
        f"주봉 VCP 관찰 구간 {weeks}주",
        f"1차 국소 고점 전 {prior_gain_weeks}주 종가 상승률 {prior_gain * 100:.1f}%",
        f"수축 횟수 {len(contractions)}회",
        "수축 낙폭 " + " -> ".join(f"{depth * 100:.1f}%" for depth in depths),
        "국소 고점 봉 " + ", ".join(str(item["peak_index"] + 1) for item in contractions),
        f"마지막 수축 낙폭 {last_depth * 100:.1f}%, 기간 {last_contraction['duration']}주",
        f"마지막 수축 거래량/첫 수축 거래량 {last_volume_ratio * 100:.1f}%",
        f"피벗가격 {pivot:.2f}, 피벗 돌파율 {pivot_breakout * 100:.1f}%",
        f"MA10/30/40 {'정배열' if ma_bullish else '상승 구조' if ma_rising else '약함'}",
    ]
    return score_result(breakdown, evidence, {"start": max(0, contractions[0]["peak_index"] - 8)})


def find_vcp_first_peak(c: list[dict[str, Any]], start: int, end: int) -> tuple[int, float, int] | None:
    candidates = []
    for index in range(start, max(start, end - 5)):
        gain, weeks = vcp_prior_close_gain_at(c, index)
        if gain >= 0.30:
            candidates.append((index, gain, weeks))
    if not candidates:
        return None
    peak_index, prior_gain, prior_gain_weeks = max(candidates, key=lambda item: (c[item[0]]["close"], -item[0]))
    return peak_index, prior_gain, prior_gain_weeks


def vcp_prior_close_gain_at(c: list[dict[str, Any]], peak_index: int) -> tuple[float, int]:
    peak_close = c[peak_index]["close"]
    candidates = []
    for weeks in range(2, 6):
        previous_index = peak_index - weeks
        if previous_index < 0:
            continue
        gain = peak_close / max(1, c[previous_index]["close"]) - 1
        candidates.append((gain, weeks))
    return max(candidates, key=lambda item: item[0]) if candidates else (0, 0)


def find_vcp_contractions(c: list[dict[str, Any]], first_peak_index: int, end: int) -> list[dict[str, Any]]:
    pivot_highs = [first_peak_index]
    reference_close = c[first_peak_index]["close"]
    while len(pivot_highs) < 6:
        next_peak = find_next_vcp_peak(c, pivot_highs[-1] + 2, end, reference_close)
        if next_peak is None:
            break
        pivot_highs.append(next_peak)

    contractions: list[dict[str, Any]] = []
    for position, peak_index in enumerate(pivot_highs):
        next_peak_index = pivot_highs[position + 1] if position + 1 < len(pivot_highs) else end
        if next_peak_index <= peak_index + 1:
            continue
        trough_end = next_peak_index - 1 if position + 1 < len(pivot_highs) else next_peak_index
        trough_index = min(range(peak_index + 1, trough_end + 1), key=lambda item: c[item]["close"])
        peak_close = c[peak_index]["close"]
        trough_close = c[trough_index]["close"]
        depth = peak_close / max(1, trough_close) - 1
        if depth < 0.04:
            continue
        segment = c[peak_index : trough_index + 1]
        contractions.append(
            {
                "peak_index": peak_index,
                "trough_index": trough_index,
                "peak_close": peak_close,
                "trough_close": trough_close,
                "depth": depth,
                "duration": trough_index - peak_index + 1,
                "avg_volume": avg(item["volume"] for item in segment),
            }
        )
    return contractions


def find_next_vcp_peak(c: list[dict[str, Any]], search_start: int, end: int, reference_close: float) -> int | None:
    for index in range(search_start, end):
        ratio = c[index]["close"] / max(1, reference_close)
        if 0.95 <= ratio <= 1.05 and is_vcp_local_peak(c, index, search_start, end):
            return index
    return None


def is_vcp_local_peak(c: list[dict[str, Any]], index: int, start: int, end: int) -> bool:
    left = max(start, index - 5)
    right = min(end, index + 5)
    close = c[index]["close"]
    return close == max(c[near]["close"] for near in range(left, right + 1))


def vcp_pivot_price(c: list[dict[str, Any]], peak_indices: list[int], target_index: int) -> float | None:
    if len(peak_indices) < 2:
        return None
    first_index = peak_indices[0]
    last_index = peak_indices[-1]
    if last_index == first_index:
        return None
    first_close = c[first_index]["close"]
    last_close = c[last_index]["close"]
    slope = (last_close - first_close) / (last_index - first_index)
    return first_close + slope * (target_index - first_index)


def evaluate_flag(c: list[dict[str, Any]], i: int) -> dict[str, Any] | None:
    pole_days = 10
    flag_days = 10
    start = i - pole_days - flag_days + 1
    if start < 0:
        return None
    pole = c[start : start + pole_days]
    flag = c[start + pole_days : i + 1]
    pole_low = min(x["low"] for x in pole)
    pole_high = max(x["close"] for x in pole)
    pole_gain = pole_high / max(1, pole_low) - 1
    if pole_gain < 0.20:
        return None
    flag_low = min(x["low"] for x in flag[:-1])
    retrace = (pole_high - flag_low) / max(1, pole_high - pole_low)
    if retrace > 0.60:
        return None
    channel_high = max(x["close"] for x in flag[:-1])
    breakout = c[i]["close"] / max(1, channel_high) - 1
    if breakout < 0.02:
        return None
    flag_volume_ratio = avg(x["volume"] for x in flag[:-1]) / max(1, avg(x["volume"] for x in pole))
    high_slope_down = flag[-2]["high"] <= flag[0]["high"] * 1.03
    low_slope_down = flag_low <= flag[0]["low"] * 1.03
    breakdown = {
        "pole_strength": 20 if pole_gain >= 0.35 else 15,
        "flag_duration": 10,
        "retracement_control": 20 if retrace <= 0.38 else 14 if retrace <= 0.50 else 8,
        "channel_slope": 15 if high_slope_down and low_slope_down else 8,
        "volume_dry_up": 15 if flag_volume_ratio <= 0.75 else 10 if flag_volume_ratio <= 0.95 else 5,
        "breakout_strength": 15 if breakout >= 0.05 else 10,
        "ma_support": 5 if c[i]["close"] >= c[i]["ma50"] else 0,
    }
    evidence = [
        f"상승 기둥 {pole_days}거래일 상승률 {pole_gain * 100:.1f}%",
        f"플래그 형성 {flag_days}거래일",
        f"기둥 대비 되돌림 {retrace * 100:.1f}%",
        f"조정 거래량/기둥 거래량 {flag_volume_ratio * 100:.1f}%",
        f"채널 상단 돌파율 {breakout * 100:.1f}%",
    ]
    return score_result(breakdown, evidence, {"start": start})


def evaluate_inverse_head_shoulders(c: list[dict[str, Any]], i: int) -> dict[str, Any] | None:
    start = i - 80
    if start < 0:
        return None
    w = c[start : i + 1]
    left_range = range(10, 30)
    head_range = range(30, 55)
    right_range = range(55, 75)
    left = min(left_range, key=lambda idx: w[idx]["close"])
    head = min(head_range, key=lambda idx: w[idx]["close"])
    right = min(right_range, key=lambda idx: w[idx]["close"])
    left_close = w[left]["close"]
    head_close = w[head]["close"]
    right_close = w[right]["close"]
    if head_close >= left_close * 0.95 or head_close >= right_close * 0.95:
        return None
    shoulder_ratio = right_close / max(1, left_close)
    if shoulder_ratio < 0.85 or shoulder_ratio > 1.15:
        return None
    neckline = max(max(x["close"] for x in w[left:head]), max(x["close"] for x in w[head:right]))
    breakout = c[i]["close"] / max(1, neckline) - 1
    if breakout < 0.02:
        return None
    prior_high = max(x["close"] for x in c[max(0, start - 40) : start + 1])
    prior_down = prior_high / max(1, head_close) - 1
    if prior_down < 0.15:
        return None
    volume_ratio = c[i]["volume"] / max(1, c[i]["volume_ma20"])
    breakdown = {
        "prior_downtrend": 15 if prior_down >= 0.25 else 10,
        "head_depth": 20 if min(left_close, right_close) / head_close - 1 >= 0.12 else 14,
        "shoulder_balance": 15 if 0.90 <= shoulder_ratio <= 1.10 else 10,
        "right_shoulder_strength": 15 if right_close >= head_close * 1.10 else 10,
        "neckline_breakout": 20 if breakout >= 0.05 else 14,
        "volume_recovery": 10 if volume_ratio >= 1.2 else 6 if volume_ratio >= 1.0 else 0,
        "ma_recovery": 5 if c[i]["close"] >= c[i]["ma50"] else 0,
    }
    evidence = [
        f"선행 하락률 {prior_down * 100:.1f}%",
        f"머리 저점/어깨 저점 깊이 {min(left_close, right_close) / head_close * 100:.1f}%",
        f"오른쪽 어깨/왼쪽 어깨 비율 {shoulder_ratio * 100:.1f}%",
        f"neckline 돌파율 {breakout * 100:.1f}%",
        f"돌파 거래량/20일 평균 {volume_ratio * 100:.1f}%",
    ]
    return score_result(breakdown, evidence, {"start": start})


def evaluate_moving_average_breakout(c: list[dict[str, Any]], i: int) -> dict[str, Any] | None:
    last = c[i]
    target = "ma200" if last["close"] > last["ma200"] and c[i - 1]["close"] <= c[i - 1]["ma200"] else "ma150" if last["close"] > last["ma150"] and c[i - 1]["close"] <= c[i - 1]["ma150"] else "ma50" if last["close"] > last["ma50"] and c[i - 1]["close"] <= c[i - 1]["ma50"] else ""
    if not target:
        return None
    ma_value = last[target]
    strength = last["close"] / max(1, ma_value) - 1
    if strength < 0.02:
        return None
    prior_below = sum(1 for x in c[i - 20 : i] if x["close"] < x[target])
    if prior_below < 8:
        return None
    volume_ratio = last["volume"] / max(1, last["volume_ma20"])
    close_position = candle_close_position(last)
    runup = last["close"] / max(1, min(x["low"] for x in c[i - 10 : i])) - 1
    breakdown = {
        "prior_below_ma": 15 if prior_below >= 14 else 10,
        "breakout_ma_level": 20 if target == "ma200" else 16 if target == "ma150" else 12,
        "close_strength": 15 if strength >= 0.06 else 10 if strength >= 0.04 else 7,
        "ma_slope_improvement": 15 if last["ma50"] >= c[i - 10]["ma50"] else 8,
        "volume_confirmation": 15 if volume_ratio >= 1.5 else 10 if volume_ratio >= 1.0 else 5,
        "body_quality": 10 if last["close"] > last["open"] and close_position >= 0.65 else 5,
        "overheat_control": 10 if runup <= 0.18 else 5,
    }
    evidence = [
        f"{target.upper()} 종가 돌파",
        f"최근 20일 중 기준선 하회 {prior_below}일",
        f"종가 돌파율 {strength * 100:.1f}%",
        f"돌파 거래량/20일 평균 {volume_ratio * 100:.1f}%",
        f"돌파 전 10일 저점 대비 상승률 {runup * 100:.1f}%",
    ]
    return score_result(breakdown, evidence, {"start": max(0, i - 60)})


def evaluate_volume_spike(c: list[dict[str, Any]], i: int) -> dict[str, Any] | None:
    last = c[i]
    volume_ratio = last["volume"] / max(1, last["volume_ma20"])
    if volume_ratio < 2.0:
        return None
    price_change = last["close"] / max(1, c[i - 1]["close"]) - 1
    recent_high = max(x["close"] for x in c[i - 20 : i])
    high_breakout = last["close"] / max(1, recent_high) - 1
    if price_change < 0.04 and high_breakout < 0.02 and last["close"] < last["ma50"]:
        return None
    close_position = candle_close_position(last)
    upper_wick = upper_wick_ratio(last)
    base_range = max(x["high"] for x in c[i - 30 : i]) / max(1, min(x["low"] for x in c[i - 30 : i])) - 1
    gap = last["open"] / max(1, c[i - 1]["close"]) - 1
    breakdown = {
        "volume_ratio": 25 if volume_ratio >= 5.0 else 20 if volume_ratio >= 3.0 else 15,
        "price_response": 20 if price_change >= 0.08 or high_breakout >= 0.05 else 14,
        "close_quality": 15 if close_position >= 0.75 and upper_wick <= 0.25 else 10 if upper_wick <= 0.40 else 5,
        "breakout_context": 15 if high_breakout >= 0.03 else 10 if last["close"] >= last["ma50"] else 5,
        "base_context": 10 if base_range <= 0.35 else 6,
        "ma_recovery": 10 if last["close"] >= last["ma50"] else 5,
        "risk_control": 5 if upper_wick <= 0.35 and gap <= 0.12 else 0,
    }
    evidence = [
        f"거래량/20일 평균 {volume_ratio * 100:.1f}%",
        f"전일 대비 종가 변화 {price_change * 100:.1f}%",
        f"최근 20일 고점 대비 돌파율 {high_breakout * 100:.1f}%",
        f"종가 위치 {close_position * 100:.1f}%",
        f"윗꼬리 비율 {upper_wick * 100:.1f}%",
    ]
    return score_result(breakdown, evidence, {"start": max(0, i - 60)})


def score_result(breakdown: dict[str, float], evidence: list[str], indices: dict[str, int]) -> dict[str, Any]:
    return {"score": sum(breakdown.values()), "breakdown": breakdown, "evidence": evidence, "indices": indices}


def classify_next_five(last_visible: dict[str, Any], future: list[dict[str, Any]]) -> str:
    move = future[-1]["close"] / last_visible["close"] - 1
    if move >= NEXT_FIVE_UP_THRESHOLD:
        return "up"
    if move <= NEXT_FIVE_DOWN_THRESHOLD:
        return "down"
    return "sideways"


def avg(values) -> float:
    materialized = list(values)
    return sum(materialized) / len(materialized) if materialized else 0


def candle_close_position(candle: dict[str, Any]) -> float:
    candle_range = max(1, candle["high"] - candle["low"])
    return (candle["close"] - candle["low"]) / candle_range


def upper_wick_ratio(candle: dict[str, Any]) -> float:
    candle_range = max(1, candle["high"] - candle["low"])
    return (candle["high"] - candle["close"]) / candle_range


def lower_wick_ratio(candle: dict[str, Any]) -> float:
    candle_range = max(1, candle["high"] - candle["low"])
    wick_start = candle["open"] if candle["close"] >= candle["open"] else candle["close"]
    return (wick_start - candle["low"]) / candle_range


def has_balanced_questions(scored: list[dict[str, Any]]) -> bool:
    used_codes_by_answer: dict[str, set[str]] = {answer: set() for answer in TARGET_ANSWER_COUNTS}
    for item in scored:
        answer = item["correct_answer"]
        if answer in used_codes_by_answer:
            used_codes_by_answer[answer].add(item["stock"]["code"])
    return all(len(used_codes_by_answer[answer]) >= count for answer, count in TARGET_ANSWER_COUNTS.items())


def select_balanced_questions(scored: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected_by_answer: dict[str, list[dict[str, Any]]] = {answer: [] for answer in TARGET_ANSWER_COUNTS}
    used_codes: set[str] = set()
    used_keys: set[tuple[str, str]] = set()
    for answer in QUESTION_ANSWER_ORDER:
        candidates = [
            item
            for item in scored
            if item["correct_answer"] == answer
            and item["stock"]["code"] not in used_codes
            and (item["stock"]["code"], item["base_date"]) not in used_keys
            and len(selected_by_answer[answer]) < TARGET_ANSWER_COUNTS[answer]
        ]
        if not candidates:
            candidates = [
                item
                for item in scored
                if item["correct_answer"] == answer
                and (item["stock"]["code"], item["base_date"]) not in used_keys
                and len(selected_by_answer[answer]) < TARGET_ANSWER_COUNTS[answer]
            ]
        if not candidates:
            raise RuntimeError(f"Need more {answer} questions")
        selected = max(candidates, key=lambda item: (item["score"], item["base_date"]))
        selected_by_answer[answer].append(selected)
        used_codes.add(selected["stock"]["code"])
        used_keys.add((selected["stock"]["code"], selected["base_date"]))

    ordered: list[dict[str, Any]] = []
    cursor = {answer: 0 for answer in TARGET_ANSWER_COUNTS}
    for answer in QUESTION_ANSWER_ORDER:
        ordered.append(selected_by_answer[answer][cursor[answer]])
        cursor[answer] += 1
    return ordered


def write_scorecard_sql() -> None:
    statements = []
    for slug, scorecard in SCORECARDS.items():
        statements.append(
            "UPDATE patterns\n"
            f"SET definition = jsonb_set(definition, '{{scorecard}}', {sql_json(scorecard)}::jsonb, true),\n"
            "    updated_at = now()\n"
            f"WHERE slug = {sql_quote(slug)};"
        )
    SCORECARD_SQL.write_text("\n\n".join(statements) + "\n", encoding="utf-8")


def write_question_sql(slug: str, selected: list[dict[str, Any]]) -> None:
    meta = PATTERN_META[slug]
    output_sql = SEED_DIR / meta["file"]
    values = []
    for index, item in enumerate(selected, start=1):
        stock = item["stock"]
        source_symbol = stock["yahoo_symbol"]
        source_url = f"https://finance.yahoo.com/quote/{source_symbol}"
        source_date_range = f"{item['chart_data'][0]['time']} ~ {item['actual_next_candles'][-1]['time']}"
        difficulty = "medium" if item["score"] >= 85 else "easy"
        answer_label = {"up": "상승", "sideways": "횡보", "down": "하락"}[item["correct_answer"]]
        symbol = f"{stock['code']} {stock['name']}"
        explanation = (
            f"{stock['name']}({stock['code']})의 실제 일봉 데이터에서 {meta['name']} 스코어 "
            f"{item['score']:.1f}점을 통과한 구간입니다. {meta['description']} "
            f"실제 다음 5봉 종가 기준 등락률은 {item['next_five_return'] * 100:.1f}%로, 정답은 {answer_label}입니다."
        )
        values.append(
            "\n  (\n"
            f"    '{meta['uuid_prefix']}-0000-0000-0000-{index:012d}'::uuid,\n"
            f"    {sql_quote(symbol)},\n"
            f"    {sql_quote(source_symbol)},\n"
            f"    {sql_quote(stock['market'])},\n"
            f"    {sql_quote(source_url)},\n"
            f"    {sql_quote(source_date_range)},\n"
            f"    '{difficulty}'::question_difficulty,\n"
            f"    '{item['base_date']}'::date,\n"
            f"    {sql_json(item['chart_data'])}::jsonb,\n"
            f"    {sql_json(item['actual_next_candles'])}::jsonb,\n"
            f"    '{item['correct_answer']}'::answer_direction,\n"
            f"    {sql_quote(explanation)},\n"
            f"    {item['score']:.2f},\n"
            f"    {sql_json(item['evidence'])}::jsonb,\n"
            f"    {sql_json(item['breakdown'])}::jsonb\n"
            "  )"
        )

    sql = (
        "WITH pattern_row AS (\n"
        "  SELECT id\n"
        "  FROM patterns\n"
        f"  WHERE slug = {sql_quote(slug)}\n"
        "  LIMIT 1\n"
        "),\n"
        "real_questions AS (\n"
        "  SELECT *\n"
        "  FROM (\n"
        "    VALUES"
        + ",".join(values)
        + "\n"
        "  ) AS rq(id, symbol, source_symbol, source_exchange, source_url, source_date_range, difficulty, base_date, chart_data, actual_next_candles, correct_answer, ai_explanation, rule_score, pattern_evidence, pattern_score_breakdown)\n"
        ")\n"
        "INSERT INTO questions (\n"
        "  id,\n"
        "  pattern_id,\n"
        "  symbol,\n"
        "  market,\n"
        "  timeframe,\n"
        "  difficulty,\n"
        "  market_regime,\n"
        "  base_date,\n"
        "  chart_data,\n"
        "  actual_next_candles,\n"
        "  correct_answer,\n"
        "  ai_explanation,\n"
        "  rule_score,\n"
        "  public_accuracy,\n"
        "  pattern_evidence,\n"
        "  pattern_score_breakdown,\n"
        "  is_synthetic,\n"
        "  source_name,\n"
        "  source_url,\n"
        "  source_symbol,\n"
        "  source_exchange,\n"
        "  source_date_range\n"
        ")\n"
        "SELECT\n"
        "  rq.id,\n"
        "  p.id,\n"
        "  rq.symbol,\n"
        "  'KRX',\n"
        f"  {sql_quote(meta['timeframe'])},\n"
        "  rq.difficulty,\n"
        f"  {sql_quote(meta['market_regime'])}::market_regime,\n"
        "  rq.base_date,\n"
        "  rq.chart_data,\n"
        "  rq.actual_next_candles,\n"
        "  rq.correct_answer,\n"
        "  rq.ai_explanation,\n"
        "  rq.rule_score,\n"
        "  0.7000,\n"
        "  rq.pattern_evidence,\n"
        "  rq.pattern_score_breakdown,\n"
        "  false,\n"
        "  'Yahoo Finance chart API',\n"
        "  rq.source_url,\n"
        "  rq.source_symbol,\n"
        "  rq.source_exchange,\n"
        "  rq.source_date_range\n"
        "FROM real_questions rq\n"
        "CROSS JOIN pattern_row p\n"
        "ON CONFLICT (id) DO UPDATE SET\n"
        "  pattern_id = EXCLUDED.pattern_id,\n"
        "  symbol = EXCLUDED.symbol,\n"
        "  market = EXCLUDED.market,\n"
        "  timeframe = EXCLUDED.timeframe,\n"
        "  difficulty = EXCLUDED.difficulty,\n"
        "  market_regime = EXCLUDED.market_regime,\n"
        "  base_date = EXCLUDED.base_date,\n"
        "  chart_data = EXCLUDED.chart_data,\n"
        "  actual_next_candles = EXCLUDED.actual_next_candles,\n"
        "  correct_answer = EXCLUDED.correct_answer,\n"
        "  ai_explanation = EXCLUDED.ai_explanation,\n"
        "  rule_score = EXCLUDED.rule_score,\n"
        "  public_accuracy = EXCLUDED.public_accuracy,\n"
        "  pattern_evidence = EXCLUDED.pattern_evidence,\n"
        "  pattern_score_breakdown = EXCLUDED.pattern_score_breakdown,\n"
        "  is_synthetic = EXCLUDED.is_synthetic,\n"
        "  source_name = EXCLUDED.source_name,\n"
        "  source_url = EXCLUDED.source_url,\n"
        "  source_symbol = EXCLUDED.source_symbol,\n"
        "  source_exchange = EXCLUDED.source_exchange,\n"
        "  source_date_range = EXCLUDED.source_date_range,\n"
        "  is_active = true,\n"
        "  updated_at = now();\n"
    )
    output_sql.write_text(sql, encoding="utf-8")
    print(f"wrote_sql={output_sql}", flush=True)


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_json(value: Any) -> str:
    return sql_quote(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
