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
LIMIT_FIVE_ANSWER_COUNTS = {"up": 3, "sideways": 1, "down": 1}
LIMIT_FIVE_ANSWER_ORDER = ["up", "down", "up", "sideways", "up"]
PAGES_PER_MARKET = 20
MAX_WORKERS = 48
FETCH_TIMEOUT_SECONDS = 6
MIN_SCORE = 75

PATTERN_ORDER = [
    "pullback",
    "triangle",
    "flag",
    "flat-base",
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
        "timeframe": "1w",
        "description": "마크 미너비니의 VCP 관점으로, 주봉에서 수축폭과 거래량이 단계적으로 줄어드는 구조를 기준으로 선별합니다.",
    },
    "flag": {
        "name": "깃발형",
        "file": "real_flag_questions.sql",
        "uuid_prefix": "29000000",
        "market_regime": "bull",
        "timeframe": "1w",
        "description": "High Tight Flag 관점으로, 주봉 4~8주 급등 이후 조정 구간이 MA10주 근처로 들어오는 구조를 기준으로 선별했습니다.",
    },
    "flat-base": {
        "name": "플랫베이스",
        "file": "real_flat_base_questions.sql",
        "uuid_prefix": "30000000",
        "market_regime": "bull",
        "timeframe": "1w",
        "description": "VCP와 동일한 선행 상승 조건 이후, 15% 이내 조정 범위에서 주간 종가 변동성이 3주 연속 1.5% 이내로 압축되는 Flat Base 구조를 기준으로 선별합니다.",
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
            {"key": "contraction_count", "label": "국소 고점/수축 횟수", "max_points": 10, "description": "국소 고점은 최소 3개 이상이어야 하며, 종가 기준 수축 구간은 2~5회 확인되어야 합니다."},
            {"key": "contraction_depths", "label": "수축폭 감소", "max_points": 25, "description": "뒤로 갈수록 각 수축의 낙폭이 작아져야 합니다."},
            {"key": "volume_dry_up", "label": "거래량 감소", "max_points": 15, "description": "수축이 진행될수록 거래량이 줄어들면 점수가 높습니다."},
            {"key": "last_contraction_quality", "label": "마지막 수축 품질", "max_points": 15, "description": "마지막 수축이 좁고 짧으며 매물 압력이 작을수록 점수가 높습니다."},
            {"key": "ma_structure", "label": "이동평균선 정배열", "max_points": 10, "description": "주봉 MA10 > MA30 > MA40 정배열 상태여야 합니다."},
            {"key": "pivot_quality", "label": "피벗 돌파 품질", "max_points": 10, "description": "피벗 돌파봉 거래량이 직전 봉 대비 150% 이상이어야 하며, 윗꼬리는 짧을수록 점수가 높습니다."},
        ],
    },
    "flag": {
        "max_score": 100,
        "primary_threshold": 75,
        "high_confidence_threshold": 85,
        "criteria": [
            {"key": "surge_strength", "label": "선행 급등 강도", "max_points": 25, "description": "주봉 4~8주 안에 저점 종가 대비 고점봉 종가가 80~100% 이상 급등해야 합니다."},
            {"key": "surge_volume", "label": "선행 급등 거래량", "max_points": 15, "description": "급등 구간 평균 거래량이 직전 평균 대비 150% 이상 증가해야 합니다."},
            {"key": "flag_depth", "label": "깃발 조정 깊이", "max_points": 20, "description": "급등 고점봉 종가 대비 조정 구간 최저 종가 낙폭이 20% 이내여야 합니다."},
            {"key": "ma10_touch", "label": "10주선 근접", "max_points": 15, "description": "조정 구간 중 종가가 MA10주 플러스마이너스 5% 안으로 처음 들어온 봉을 문제 마지막 봉으로 봅니다."},
            {"key": "volume_spike_control", "label": "조정 거래량 급증 제한", "max_points": 15, "description": "조정 구간의 각 봉 거래량이 직전 봉 거래량의 200%를 넘지 않아야 합니다."},
            {"key": "ma10_support", "label": "10주선 방어", "max_points": 10, "description": "조정 구간 종가가 MA10주보다 5% 이상 아래로 하락하면 후보에서 제외합니다."},
        ],
    },
    "flat-base": {
        "max_score": 100,
        "primary_threshold": 75,
        "high_confidence_threshold": 85,
        "criteria": [
            {"key": "prior_uptrend", "label": "선행 상승", "max_points": 20, "description": "VCP와 동일하게 선행 고점 전 2~5주 주봉 종가 기준 상승률이 30% 이상이어야 합니다."},
            {"key": "base_depth", "label": "베이스 조정폭", "max_points": 20, "description": "베이스 구간의 종가 기준 최대 조정폭은 선행 상승 고점 종가 대비 15% 이내여야 합니다."},
            {"key": "three_week_tightness", "label": "3주 종가 압축", "max_points": 25, "description": "주간 종가 기준 최근 3주 변동폭이 1.5% 이내이면 플랫베이스 핵심 조건을 충족합니다."},
            {"key": "last_candle_rule", "label": "문제 마지막 봉", "max_points": 10, "description": "3주 종가 압축이 완성되는 세 번째 주봉을 문제의 마지막 봉으로 사용합니다."},
            {"key": "ma_structure", "label": "10/30/40주선 구조", "max_points": 15, "description": "주봉 차트에는 MA10, MA30, MA40을 표시하고 상승 추세에 어울리는 배열일수록 점수가 높습니다."},
            {"key": "volume_control", "label": "거래량 안정", "max_points": 10, "description": "베이스 구간에서 과도한 매물 출회 없이 거래량이 안정될수록 점수가 높습니다."},
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
    {"key": "contraction_count", "label": "국소 고점/수축 횟수", "max_points": 10, "description": "국소 고점은 최소 3개 이상이어야 하며, 종가 기준 수축 구간은 2~5회 확인되어야 합니다."},
    {"key": "contraction_depths", "label": "수축폭 감소", "max_points": 25, "description": "1차 -45%, 2차 -33%, 3차 -25%, 4차 -15%, 5차 -8% 한도 안에서 뒤로 갈수록 수축폭이 작아져야 합니다."},
    {"key": "volume_dry_up", "label": "거래량 감소", "max_points": 15, "description": "수축이 진행될수록 거래량이 줄어들면 점수가 높습니다."},
    {"key": "last_contraction_quality", "label": "마지막 수축 품질", "max_points": 15, "description": "마지막 수축은 좁고 짧을수록 좋으며, 5차 수축은 최대 -8%까지만 허용합니다."},
    {"key": "ma_structure", "label": "이동평균선 정배열", "max_points": 10, "description": "주봉 MA10 > MA30 > MA40 정배열 상태여야 합니다."},
    {"key": "pivot_quality", "label": "피벗 돌파 품질", "max_points": 10, "description": "피벗 돌파봉 거래량이 직전 봉 대비 150% 이상이어야 하며, 윗꼬리는 짧을수록 점수가 높습니다."},
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
    question_limit = parse_question_limit(sys.argv[1:])
    answer_counts, answer_order = answer_plan(question_limit)
    target_slugs = [slug for slug in sys.argv[1:] if slug in PATTERN_ORDER] or PATTERN_ORDER
    stocks = load_listed_stocks(PAGES_PER_MARKET)
    print(f"listed_candidates={len(stocks)}", flush=True)
    print(f"target_patterns={','.join(target_slugs)}", flush=True)
    print(f"question_limit={question_limit}", flush=True)

    scored: dict[str, list[dict[str, Any]]] = {slug: [] for slug in target_slugs}
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    futures = {}
    try:
        futures = {executor.submit(scan_stock, stock, target_slugs): stock for stock in stocks}
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
            if all(has_balanced_questions(items, answer_counts) for items in scored.values()):
                print(f"balanced_candidates_ready_at={index}", flush=True)
                break
    finally:
        for future in futures:
            future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)

    selected_by_slug: dict[str, list[dict[str, Any]]] = {}
    for slug in target_slugs:
        selected = select_balanced_questions(scored[slug], answer_counts, answer_order)
        selected_by_slug[slug] = selected
        counts = {answer: sum(1 for item in selected if item["correct_answer"] == answer) for answer in answer_counts}
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
    with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:  # noqa: S310
        return response.read().decode(encoding, errors="ignore")


def fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=REQUEST_HEADERS)
    with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:  # noqa: S310
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


def scan_stock(stock: ListedStock, target_slugs: list[str] | None = None) -> dict[str, list[dict[str, Any]]]:
    target_set = set(target_slugs or PATTERN_ORDER)
    weekly_slugs = {"triangle", "flag", "flat-base"}
    daily_candles = fetch_daily_candles(stock.yahoo_symbol) if target_set - weekly_slugs else []
    weekly_candles = fetch_weekly_candles(stock.yahoo_symbol) if target_set & weekly_slugs else []
    if len(daily_candles) < 260 and len(weekly_candles) < 80:
        return {slug: [] for slug in PATTERN_ORDER}

    daily_evaluators: dict[str, Callable[[list[dict[str, Any]], int], dict[str, Any] | None]] = {
        "pullback": evaluate_pullback,
        "moving-average-breakout": evaluate_moving_average_breakout,
        "volume-spike": evaluate_volume_spike,
    }
    best: dict[str, dict[str, dict[str, Any]]] = {slug: {} for slug in PATTERN_ORDER}

    active_daily_evaluators = {slug: evaluator for slug, evaluator in daily_evaluators.items() if slug in target_set}
    if active_daily_evaluators:
        scan_candle_series(stock, daily_candles, active_daily_evaluators, best)
    weekly_evaluators = {}
    if "triangle" in target_set:
        weekly_evaluators["triangle"] = evaluate_triangle
    if "flag" in target_set:
        weekly_evaluators["flag"] = evaluate_flag
    if "flat-base" in target_set:
        weekly_evaluators["flat-base"] = evaluate_flat_base
    if weekly_evaluators:
        scan_candle_series(stock, weekly_candles, weekly_evaluators, best, min_index=60)
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
    pivot_peak_indices = contractions[0].get("pivot_high_indices", [item["peak_index"] for item in contractions])
    if len(pivot_peak_indices) < 3:
        return None

    depths = [item["depth"] for item in contractions]
    max_allowed_depths = [0.45, 0.33, 0.25, 0.15, 0.08]
    if any(depth > max_allowed_depths[index] for index, depth in enumerate(depths)):
        return None
    if any(depths[index + 1] >= depths[index] for index in range(len(depths) - 1)):
        return None

    trough_closes = [item["trough_close"] for item in contractions]
    if any(trough_closes[index] < trough_closes[index - 1] * 0.90 for index in range(1, len(trough_closes))):
        return None

    avg_volumes = [item["avg_volume"] for item in contractions]

    peak_indices = pivot_peak_indices
    pivot = vcp_pivot_price(c, peak_indices, i)
    if pivot is None:
        return None
    pivot_breakout = last["close"] / max(1, pivot) - 1
    if pivot_breakout < 0 or pivot_breakout > 0.08:
        return None
    pivot_volume_ratio = last["volume"] / max(1, c[i - 1]["volume"])
    if pivot_volume_ratio < 1.50:
        return None
    pivot_upper_wick = upper_wick_ratio(last)
    if pivot_upper_wick >= 0.50:
        return None

    ma_bullish = last["ma10"] > last["ma30"] > last["ma40"]
    if not ma_bullish:
        return None

    last_contraction = contractions[-1]
    last_depth = last_contraction["depth"]
    depths_decreasing = sum(1 for index in range(len(depths) - 1) if depths[index + 1] <= depths[index])
    last_volume_ratio = avg_volumes[-1] / max(1, avg_volumes[0])
    volume_steps_down = sum(1 for index in range(len(avg_volumes) - 1) if avg_volumes[index + 1] <= avg_volumes[index])

    breakdown = {
        "prior_uptrend": 15 if prior_gain >= 0.45 else 10,
        "contraction_count": 10,
        "contraction_depths": 25 if depths_decreasing == len(depths) - 1 and depths[-1] <= depths[0] * 0.65 else 18,
        "volume_dry_up": 15 if volume_steps_down == len(avg_volumes) - 1 and last_volume_ratio <= 0.75 else 10 if last_volume_ratio <= 0.90 else 5,
        "last_contraction_quality": 15 if last_depth <= 0.08 and last_contraction["duration"] <= 6 else 10,
        "ma_structure": 10,
        "pivot_quality": 10 if pivot_upper_wick <= 0.05 else 8 if pivot_upper_wick <= 0.15 else 6 if pivot_upper_wick <= 0.30 else 3,
    }
    evidence = [
        f"주봉 VCP 관찰 구간 {weeks}주",
        f"1차 국소 고점 전 {prior_gain_weeks}주 종가 상승률 {prior_gain * 100:.1f}%",
        f"국소 고점 {len(peak_indices)}개",
        "수축 낙폭 " + " / ".join(f"{depth * 100:.1f}%" for depth in depths),
        f"마지막 수축 낙폭 {last_depth * 100:.1f}%, 기간 {last_contraction['duration']}주",
        f"마지막 수축 거래량/첫 수축 거래량 {last_volume_ratio * 100:.1f}%",
        f"피벗가격 {pivot:.2f}, 피벗 돌파율 {pivot_breakout * 100:.1f}%",
        f"피벗 돌파 거래량/직전 봉 거래량 {pivot_volume_ratio * 100:.1f}%",
        f"피벗 돌파봉 윗꼬리 비율 {pivot_upper_wick * 100:.1f}%",
        "MA10/30/40 정배열",
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


def evaluate_flat_base(c: list[dict[str, Any]], i: int) -> dict[str, Any] | None:
    if i < 60:
        return None
    tight_closes = [c[index]["close"] for index in range(i - 2, i + 1)]
    tight_avg_close = sum(tight_closes) / len(tight_closes)
    tight_range = (max(tight_closes) - min(tight_closes)) / max(1, tight_avg_close)
    if tight_range > 0.015:
        return None

    observation_start = max(5, i - 49)
    tight_start = i - 2
    peak_candidates: list[tuple[int, float, int]] = []
    for peak_index in range(observation_start, tight_start):
        prior_gain, prior_gain_weeks = vcp_prior_close_gain_at(c, peak_index)
        if prior_gain >= 0.30:
            peak_candidates.append((peak_index, prior_gain, prior_gain_weeks))
    if not peak_candidates:
        return None

    peak_index, prior_gain, prior_gain_weeks = max(
        peak_candidates,
        key=lambda item: (c[item[0]]["close"], item[0]),
    )
    peak_close = c[peak_index]["close"]
    base = c[peak_index + 1 : i + 1]
    if len(base) < 3:
        return None
    base_low_close = min(item["close"] for item in base)
    base_depth = max(0.0, (peak_close - base_low_close) / max(1, peak_close))
    if base_depth > 0.15:
        return None

    last = c[i]
    ma_structure_score = 15 if last["ma10"] > last["ma30"] > last["ma40"] else 10 if last["close"] >= last["ma10"] and last["ma10"] >= last["ma30"] else 5
    base_volume = sum(item["volume"] for item in base) / len(base)
    prior_volume_window = c[max(0, peak_index - 10) : peak_index + 1]
    prior_volume = sum(item["volume"] for item in prior_volume_window) / max(1, len(prior_volume_window))
    volume_ratio = base_volume / max(1, prior_volume)

    breakdown = {
        "prior_uptrend": 20 if prior_gain >= 0.45 else 15,
        "base_depth": 20 if base_depth <= 0.08 else 15 if base_depth <= 0.12 else 10,
        "three_week_tightness": 25 if tight_range <= 0.010 else 20,
        "last_candle_rule": 10,
        "ma_structure": ma_structure_score,
        "volume_control": 10 if volume_ratio <= 0.75 else 7 if volume_ratio <= 1.0 else 4,
    }
    evidence = [
        f"선행 고점 전 {prior_gain_weeks}주 종가 상승률 {prior_gain * 100:.1f}%",
        f"베이스 종가 기준 조정 낙폭 {base_depth * 100:.1f}%",
        f"최근 3주 종가 변동폭 {tight_range * 100:.2f}%",
        f"3주 종가 압축 완성 봉을 문제 마지막 봉으로 사용",
        f"MA10/30/40 구조 점수 {ma_structure_score}/15",
        f"베이스 평균 거래량/선행 고점 전후 평균 {volume_ratio * 100:.1f}%",
    ]
    return score_result(breakdown, evidence, {"start": max(0, peak_index - prior_gain_weeks)})


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
    for contraction in contractions:
        contraction["pivot_high_indices"] = pivot_highs
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
    best: dict[str, Any] | None = None
    for flag_weeks in range(1, min(52, i - 20) + 1):
        flag_start = i - flag_weeks + 1
        if flag_start <= 20:
            continue
        for surge_weeks in range(4, 9):
            surge_start = flag_start - surge_weeks
            if surge_start < 20:
                continue
            surge = c[surge_start:flag_start]
            flag = c[flag_start : i + 1]
            prior = c[max(0, surge_start - 20) : surge_start]
            if len(surge) != surge_weeks or len(flag) != flag_weeks or len(prior) < 10:
                continue

            surge_low_close = min(x["close"] for x in surge)
            peak_offset, peak_candle = max(enumerate(surge), key=lambda item: item[1]["close"])
            peak_close = peak_candle["close"]
            surge_gain = peak_close / max(1, surge_low_close) - 1
            if surge_gain < 0.80:
                continue

            surge_volume_ratio = avg(x["volume"] for x in surge) / max(1, avg(x["volume"] for x in prior))
            if surge_volume_ratio < 1.50:
                continue

            flag_closes = [x["close"] for x in flag]
            flag_high_close = max(flag_closes)
            flag_low_close = min(flag_closes)
            flag_depth = (peak_close - flag_low_close) / max(1, peak_close)
            if flag_depth > 0.20:
                continue

            volume_ratios = [
                flag[index]["volume"] / max(1, flag[index - 1]["volume"])
                for index in range(1, len(flag))
            ]
            previous_to_first_volume_ratio = flag[0]["volume"] / max(1, c[flag_start - 1]["volume"])
            all_volume_ratios = [previous_to_first_volume_ratio, *volume_ratios]
            max_flag_volume_ratio = max(all_volume_ratios)
            if max_flag_volume_ratio > 2.0:
                continue

            ma10_distances = [
                candle["close"] / max(1, candle.get("ma10", 0)) - 1
                for candle in flag
                if candle.get("ma10", 0)
            ]
            if len(ma10_distances) != len(flag) or min(ma10_distances) < -0.05:
                continue
            if abs(ma10_distances[-1]) > 0.05:
                continue
            if any(abs(distance) <= 0.05 for distance in ma10_distances[:-1]):
                continue

            breakdown = {
                "surge_strength": 25 if surge_gain >= 1.0 else 20,
                "surge_volume": 15 if surge_volume_ratio >= 2.0 else 10,
                "flag_depth": 20 if flag_depth <= 0.12 else 14 if flag_depth <= 0.16 else 10,
                "ma10_touch": 15 if abs(ma10_distances[-1]) <= 0.02 else 10,
                "volume_spike_control": 15 if max_flag_volume_ratio <= 1.3 else 10 if max_flag_volume_ratio <= 1.6 else 6,
                "ma10_support": 10 if min(ma10_distances) >= 0 else 6,
            }
            evidence = [
                f"주봉 {surge_weeks}주 급등률 {surge_gain * 100:.1f}%",
                f"급등 거래량/직전 평균 {surge_volume_ratio * 100:.1f}%",
                f"깃발 조정 {flag_weeks}주 후 MA10주 ±5% 첫 진입",
                f"종가 기준 조정 낙폭 {flag_depth * 100:.1f}%",
                f"조정 최고 종가/급등 고점 종가 {flag_high_close / max(1, peak_close) * 100:.1f}%",
                f"조정 구간 최대 거래량/직전 봉 거래량 {max_flag_volume_ratio * 100:.1f}%",
                f"조정 종가/MA10주 최저 이격 {min(ma10_distances) * 100:.1f}%",
                f"마지막 봉 종가/MA10주 이격 {ma10_distances[-1] * 100:.1f}%",
            ]
            result = score_result(breakdown, evidence, {"start": surge_start})
            if best is None or result["score"] > best["score"]:
                best = result
    return best


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
    wick_start = candle["close"] if candle["close"] >= candle["open"] else candle["open"]
    return (candle["high"] - wick_start) / candle_range


def lower_wick_ratio(candle: dict[str, Any]) -> float:
    candle_range = max(1, candle["high"] - candle["low"])
    wick_start = candle["open"] if candle["close"] >= candle["open"] else candle["close"]
    return (wick_start - candle["low"]) / candle_range


def parse_question_limit(args: list[str]) -> int:
    for arg in args:
        if arg.startswith("--limit="):
            return int(arg.split("=", 1)[1])
    return 10


def answer_plan(question_limit: int) -> tuple[dict[str, int], list[str]]:
    if question_limit == 5:
        return LIMIT_FIVE_ANSWER_COUNTS, LIMIT_FIVE_ANSWER_ORDER
    if question_limit != 10:
        raise ValueError("Only --limit=5 or --limit=10 is supported")
    return TARGET_ANSWER_COUNTS, QUESTION_ANSWER_ORDER


def has_balanced_questions(scored: list[dict[str, Any]], answer_counts: dict[str, int]) -> bool:
    used_codes_by_answer: dict[str, set[str]] = {answer: set() for answer in answer_counts}
    for item in scored:
        answer = item["correct_answer"]
        if answer in used_codes_by_answer:
            used_codes_by_answer[answer].add(item["stock"]["code"])
    return all(len(used_codes_by_answer[answer]) >= count for answer, count in answer_counts.items())


def select_balanced_questions(
    scored: list[dict[str, Any]],
    answer_counts: dict[str, int],
    answer_order: list[str],
) -> list[dict[str, Any]]:
    selected_by_answer: dict[str, list[dict[str, Any]]] = {answer: [] for answer in answer_counts}
    used_codes: set[str] = set()
    used_keys: set[tuple[str, str]] = set()
    for answer in answer_order:
        candidates = [
            item
            for item in scored
            if item["correct_answer"] == answer
            and item["stock"]["code"] not in used_codes
            and (item["stock"]["code"], item["base_date"]) not in used_keys
            and len(selected_by_answer[answer]) < answer_counts[answer]
        ]
        if not candidates:
            candidates = [
                item
                for item in scored
                if item["correct_answer"] == answer
                and (item["stock"]["code"], item["base_date"]) not in used_keys
                and len(selected_by_answer[answer]) < answer_counts[answer]
            ]
        if not candidates:
            raise RuntimeError(f"Need more {answer} questions")
        selected = max(candidates, key=lambda item: (item["score"], item["base_date"]))
        selected_by_answer[answer].append(selected)
        used_codes.add(selected["stock"]["code"])
        used_keys.add((selected["stock"]["code"], selected["base_date"]))

    ordered: list[dict[str, Any]] = []
    cursor = {answer: 0 for answer in answer_counts}
    for answer in answer_order:
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
    question_ids = []
    for index, item in enumerate(selected, start=1):
        question_id = f"{meta['uuid_prefix']}-0000-0000-0000-{index:012d}"
        question_ids.append(question_id)
        stock = item["stock"]
        source_symbol = stock["yahoo_symbol"]
        source_url = f"https://finance.yahoo.com/quote/{source_symbol}"
        source_date_range = f"{item['chart_data'][0]['time']} ~ {item['actual_next_candles'][-1]['time']}"
        difficulty = "medium" if item["score"] >= 85 else "easy"
        answer_label = {"up": "상승", "sideways": "횡보", "down": "하락"}[item["correct_answer"]]
        timeframe_label = {"1wk": "주봉", "1w": "주봉", "1d": "일봉"}.get(meta["timeframe"], meta["timeframe"])
        symbol = f"{stock['code']} {stock['name']}"
        explanation = (
            f"{stock['name']}({stock['code']})의 실제 {timeframe_label} 데이터에서 {meta['name']} 스코어 "
            f"{item['score']:.1f}점을 통과한 구간입니다. {meta['description']} "
            f"실제 다음 5봉 종가 기준 등락률은 {item['next_five_return'] * 100:.1f}%로, 정답은 {answer_label}입니다."
        )
        values.append(
            "\n  (\n"
            f"    '{question_id}'::uuid,\n"
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

    active_id_list = ", ".join(f"'{question_id}'::uuid" for question_id in question_ids)
    deactivate_sql = (
        "\n\nUPDATE questions\n"
        "SET is_active = false,\n"
        "    updated_at = now()\n"
        f"WHERE pattern_id = (SELECT id FROM patterns WHERE slug = {sql_quote(slug)} LIMIT 1)\n"
        "  AND source_name = 'Yahoo Finance chart API'\n"
        "  AND is_synthetic = false\n"
        f"  AND id NOT IN ({active_id_list});\n"
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
        + deactivate_sql
    )
    output_sql.write_text(sql, encoding="utf-8")
    print(f"wrote_sql={output_sql}", flush=True)


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_json(value: Any) -> str:
    return sql_quote(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
