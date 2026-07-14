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
    "bullish-engulfing",
    "early-stage2",
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
        "description": "선행 상승 이후 15% 이내 조정폭으로 쉬어가다가, 베이스 형성 중 주봉 종가가 MA10주 플러스마이너스 2% 이내에 처음 들어온 구조를 기준으로 선별합니다.",
    },
    "bullish-engulfing": {
        "name": "상승장악형",
        "file": "real_bullish_engulfing_questions.sql",
        "uuid_prefix": "31000000",
        "market_regime": "sideways",
        "timeframe": "1d",
        "description": "52주 신고가 대비 20% 이상 내려온 위치에서 음봉 뒤 양봉이 몸통을 완전히 감싸고, 두 봉 모두 앞뒤 10봉 저가 비교 하위 3개 안에 있으며, 양봉 바로 다음 봉까지의 구조를 기준으로 선별했습니다.",
    },
    "early-stage2": {
        "name": "상승초입",
        "file": "real_early_stage2_questions.sql",
        "uuid_prefix": "33000000",
        "market_regime": "bull",
        "timeframe": "1w",
        "description": "스탠 와인스타인 4단계 이론 관점으로, 1단계 베이스 이후 주봉 종가가 30주선을 회복하고 30주선 기울기가 개선되며 52주 종가 신고가로 베이스 상단 추세선을 돌파한 2단계 초입 구조를 기준으로 선별했습니다.",
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
            {"key": "prior_uptrend", "label": "선행 상승", "max_points": 20, "description": "베이스 시작 전 2~5주 주봉 종가 기준 상승률이 30% 이상이어야 합니다."},
            {"key": "base_duration", "label": "베이스 기간", "max_points": 15, "description": "베이스 기간은 최소 5주 이상이어야 하며, 6~12주면 높은 점수를 줍니다."},
            {"key": "base_depth", "label": "베이스 조정폭", "max_points": 25, "description": "베이스 전체 종가 기준 고점 대비 저점 낙폭은 15% 이내여야 합니다."},
            {"key": "three_week_tightness", "label": "3주 Tight Close", "max_points": 15, "description": "베이스 안에서 연속 3주 종가 변동폭이 1.5% 이내면 가산합니다."},
            {"key": "ma10_touch", "label": "10주선 근접", "max_points": 10, "description": "베이스 중 종가가 MA10주 플러스마이너스 2% 이내에 처음 들어온 봉을 문제 마지막 봉으로 사용합니다."},
            {"key": "ma_structure", "label": "10/30/40주선 구조", "max_points": 10, "description": "MA10 > MA30 > MA40 또는 MA10이 MA30 위에서 유지되면 점수가 높습니다."},
            {"key": "volume_control", "label": "거래량 안정성", "max_points": 5, "description": "베이스 평균 거래량이 선행 상승 구간보다 안정적이면 가산합니다."},
        ],
    },
    "bullish-engulfing": {
        "max_score": 100,
        "primary_threshold": 75,
        "high_confidence_threshold": 85,
        "criteria": [
            {"key": "engulfing_completion", "label": "몸통 장악 완성도", "max_points": 25, "description": "양봉 시가가 음봉 종가 이하이고 양봉 종가가 음봉 시가 이상이어야 하며, 장악 여유율이 클수록 점수가 높습니다."},
            {"key": "body_ratio", "label": "장악 강도", "max_points": 15, "description": "양봉 몸통 크기 / 음봉 몸통 크기 비율이 클수록 점수가 높고, 1.0배 미만은 제외합니다."},
            {"key": "location_drawdown", "label": "52주 신고가 대비 하락률", "max_points": 20, "description": "음봉 시작일 이전 252거래일 최고 종가 대비 20% 이상 하락한 위치에서 발생해야 하며, 음봉과 양봉 저가는 각각 앞뒤 10봉 저가 비교 하위 3개 안에 들어야 합니다."},
            {"key": "bearish_wick_quality", "label": "음봉 꼬리 품질", "max_points": 20, "description": "음봉 윗꼬리와 아래꼬리 비율의 합이 작을수록 점수가 높고 30% 초과는 제외합니다."},
            {"key": "bullish_wick_quality", "label": "양봉 꼬리 품질", "max_points": 20, "description": "양봉 윗꼬리와 아래꼬리 비율의 합이 작을수록 점수가 높고 30% 초과는 제외합니다."},
        ],
    },
    "early-stage2": {
        "max_score": 100,
        "primary_threshold": 75,
        "high_confidence_threshold": 85,
        "criteria": [
            {"key": "ma30_recovery", "label": "30주선 회복", "max_points": 20, "description": "주봉 종가가 MA30주 위에 있고 MA30주 대비 이격이 0~15% 범위면 높은 점수를 줍니다."},
            {"key": "ma30_slope", "label": "30주선 기울기 개선", "max_points": 20, "description": "MA30주가 8주 전 대비 평탄화 또는 상승 전환하고 최근 4주 기울기가 개선되어야 합니다."},
            {"key": "base_quality", "label": "베이스 품질", "max_points": 20, "description": "반복 저항을 만든 베이스가 길수록 가점하며, 종가 기준 조정폭은 50%까지 감점하지 않습니다."},
            {"key": "base_breakout", "label": "베이스 상단 돌파", "max_points": 15, "description": "앞뒤 5봉 기준 로컬 고가 고점들이 ±10% 안에서 반복된 상단을 만들고, 상단봉 종가 추세선을 연장한 가격을 돌파봉 종가가 돌파해야 합니다."},
            {"key": "volume_confirmation", "label": "거래량 확인", "max_points": 10, "description": "돌파 주봉 거래량은 전주 거래량 이상이어야 하며, 최근 10주 평균 대비 증가할수록 점수가 높습니다."},
            {"key": "relative_strength", "label": "상대강도 개선", "max_points": 10, "description": "최근 종가 흐름이 MA30주 대비 강해지고 저점이 높아지는 구조를 확인합니다."},
            {"key": "overheat_control", "label": "과열 제한", "max_points": 5, "description": "30주선 대비 이격과 최근 4주 상승률이 과도하지 않아야 합니다."},
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
    weekly_slugs = {"triangle", "flag", "flat-base", "early-stage2"}
    daily_candles = fetch_daily_candles(stock.yahoo_symbol) if target_set - weekly_slugs else []
    weekly_candles = fetch_weekly_candles(stock.yahoo_symbol) if target_set & weekly_slugs else []
    if len(daily_candles) < 260 and len(weekly_candles) < 80:
        return {slug: [] for slug in PATTERN_ORDER}

    daily_evaluators: dict[str, Callable[[list[dict[str, Any]], int], dict[str, Any] | None]] = {
        "pullback": evaluate_pullback,
        "bullish-engulfing": evaluate_bullish_engulfing,
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
    if "early-stage2" in target_set:
        weekly_evaluators["early-stage2"] = evaluate_early_stage2
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
                "pattern_markers": build_pattern_markers(slug, visible, score_result["indices"], start),
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
    return score_result(
        breakdown,
        evidence,
        {
            "start": trend_start_index,
            "trend_high": high_index,
            "confirmation": i,
        },
    )



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
    return score_result(
        breakdown,
        evidence,
        {
            "start": max(0, contractions[0]["peak_index"] - 8),
            "pivot_high_indices": peak_indices,
            "pivot": i,
        },
    )


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
    last = c[i]
    if last["volume"] <= 0 or last["ma10"] <= 0:
        return None

    ma10_gap = abs(last["close"] / max(1, last["ma10"]) - 1)
    if ma10_gap > 0.02:
        return None

    observation_start = max(5, i - 49)
    peak_candidates: list[tuple[int, float, int]] = []
    for peak_index in range(observation_start, i - 4):
        prior_gain, prior_gain_weeks = vcp_prior_close_gain_at(c, peak_index)
        if prior_gain >= 0.30:
            peak_candidates.append((peak_index, prior_gain, prior_gain_weeks))
    if not peak_candidates:
        return None

    best_result: dict[str, Any] | None = None
    for peak_index, prior_gain, prior_gain_weeks in peak_candidates:
        peak_close = c[peak_index]["close"]
        base_start = peak_index + 1
        base = c[base_start : i + 1]
        base_weeks = len(base)
        if base_weeks < 5 or base_weeks > 30:
            continue
        if any(item["volume"] <= 0 for item in base):
            continue
        if any(abs(item["close"] / max(1, item["ma10"]) - 1) <= 0.02 for item in base[:-1]):
            continue

        base_low_close = min(item["close"] for item in base)
        base_high_close = max(item["close"] for item in base)
        previous_base_high_close = max(item["close"] for item in base[:-1]) if len(base) > 1 else base_high_close
        base_depth = max(0.0, (base_high_close - base_low_close) / max(1, base_high_close))
        if base_depth > 0.15:
            continue
        if last["close"] > previous_base_high_close * 1.05:
            continue

        tight_score, tight_range, tight_start = best_flat_base_tight_close(base)
        ma_structure_score = (
            10
            if last["ma10"] > last["ma30"] > last["ma40"]
            else 7
            if last["ma10"] >= last["ma30"] and last["close"] >= last["ma10"] * 0.98
            else 4
        )
        base_volume = avg(item["volume"] for item in base)
        prior_volume_window = c[max(0, peak_index - 10) : peak_index + 1]
        prior_volume = avg(item["volume"] for item in prior_volume_window)
        volume_ratio = base_volume / max(1, prior_volume)

        breakdown = {
            "prior_uptrend": 20 if prior_gain >= 0.45 else 16,
            "base_duration": 15 if 6 <= base_weeks <= 12 else 12 if base_weeks <= 20 else 9,
            "base_depth": 25 if base_depth <= 0.08 else 20 if base_depth <= 0.12 else 15,
            "three_week_tightness": tight_score,
            "ma10_touch": 10 if ma10_gap <= 0.01 else 7,
            "ma_structure": ma_structure_score,
            "volume_control": 5 if volume_ratio <= 0.85 else 3 if volume_ratio <= 1.10 else 1,
        }
        evidence = [
            f"선행 고점 전 {prior_gain_weeks}주 종가 상승률 {prior_gain * 100:.1f}%",
            f"베이스 형성 {base_weeks}주",
            f"베이스 종가 기준 조정 낙폭 {base_depth * 100:.1f}%",
            f"베이스 내 3주 Tight Close 변동폭 {tight_range * 100:.2f}%",
            f"문제 마지막 봉 MA10 이격도 {ma10_gap * 100:.1f}%",
            "MA10 ±2% 첫 근접 봉을 문제 마지막 봉으로 사용",
            f"MA10/30/40 구조 점수 {ma_structure_score}/10",
            f"베이스 평균 거래량/선행 고점 전후 평균 {volume_ratio * 100:.1f}%",
        ]
        result = score_result(
            breakdown,
            evidence,
            {
                "start": max(0, peak_index - prior_gain_weeks),
                "prior_peak": peak_index,
                "base_start": base_start,
                "tight_end": base_start + tight_start + 2 if tight_start is not None else i,
                "ma10_touch": i,
            },
        )
        if best_result is None or result["score"] > best_result["score"]:
            best_result = result
    return best_result


def best_flat_base_tight_close(base: list[dict[str, Any]]) -> tuple[int, float, int | None]:
    best_range: float | None = None
    best_start: int | None = None
    for start in range(0, len(base) - 2):
        window = base[start : start + 3]
        if any(item["volume"] <= 0 for item in window):
            continue
        closes = [item["close"] for item in window]
        tight_range = max(closes) / max(1, min(closes)) - 1
        if best_range is None or tight_range < best_range:
            best_range = tight_range
            best_start = start
    if best_range is None:
        return 0, 999.0, None
    if best_range <= 0.015:
        return 15, best_range, best_start
    if best_range <= 0.025:
        return 9, best_range, best_start
    return 4, best_range, best_start


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
            result = score_result(
                breakdown,
                evidence,
                {
                    "start": surge_start,
                    "surge_start": surge_start,
                    "surge_peak": surge_start + peak_offset,
                    "flag_end": i,
                },
            )
            if best is None or result["score"] > best["score"]:
                best = result
    return best


def evaluate_bullish_engulfing(c: list[dict[str, Any]], i: int) -> dict[str, Any] | None:
    second_index = i - 1
    first_index = second_index - 1
    if first_index < 252 or i >= len(c):
        return None

    bearish = c[first_index]
    bullish = c[second_index]
    bearish_low_rank = low_rank_in_window(c, first_index, 10, 10)
    bullish_low_rank = low_rank_in_window(c, second_index, 10, 10)
    if bearish_low_rank > 3 or bullish_low_rank > 3:
        return None

    if bearish["open"] <= bearish["close"] or bullish["close"] <= bullish["open"]:
        return None
    if bearish["high"] <= bearish["low"] or bullish["high"] <= bullish["low"]:
        return None

    bearish_body = bearish["open"] - bearish["close"]
    bullish_body = bullish["close"] - bullish["open"]
    if bearish_body <= 0 or bullish_body < bearish_body:
        return None
    if bullish["open"] > bearish["close"] or bullish["close"] < bearish["open"]:
        return None

    lower_margin = (bearish["close"] - bullish["open"]) / bearish_body
    upper_margin = (bullish["close"] - bearish["open"]) / bearish_body
    if lower_margin < 0 or upper_margin < 0:
        return None
    engulfing_margin = (lower_margin + upper_margin) / 2

    prior_high_close = max(x["close"] for x in c[first_index - 252 : first_index])
    drawdown = (prior_high_close - bearish["close"]) / max(1, prior_high_close)
    if drawdown < 0.20:
        return None

    bearish_tail_sum = upper_wick_ratio(bearish) + lower_wick_ratio(bearish)
    bullish_tail_sum = upper_wick_ratio(bullish) + lower_wick_ratio(bullish)
    if bearish_tail_sum > 0.30 or bullish_tail_sum > 0.30:
        return None

    confirmation_level = min(bearish["close"], bullish["close"])
    confirmation = c[i]
    if confirmation["close"] < confirmation_level:
        return None
    confirmation_buffer = confirmation["close"] / max(1, confirmation_level) - 1

    body_ratio = bullish_body / bearish_body
    breakdown = {
        "engulfing_completion": 25 if engulfing_margin >= 0.30 else 18 if engulfing_margin >= 0.15 else 12,
        "body_ratio": 15 if body_ratio >= 2.0 else 11 if body_ratio >= 1.5 else 7,
        "location_drawdown": 20 if drawdown >= 0.40 else 16 if drawdown >= 0.30 else 12,
        "bearish_wick_quality": wick_quality_score(bearish_tail_sum),
        "bullish_wick_quality": wick_quality_score(bullish_tail_sum),
    }
    evidence = [
        f"음봉 다음 양봉 몸통 장악",
        f"하단/상단 장악 여유율 {lower_margin * 100:.1f}% / {upper_margin * 100:.1f}%",
        f"양봉 몸통/음봉 몸통 비율 {body_ratio:.2f}배",
        f"52주 최고 종가 대비 하락률 {drawdown * 100:.1f}%",
        f"음봉 꼬리 합 {bearish_tail_sum * 100:.1f}%",
        f"양봉 꼬리 합 {bullish_tail_sum * 100:.1f}%",
        f"음봉/양봉 저가 순위(앞뒤 10봉) {bearish_low_rank}위 / {bullish_low_rank}위",
        f"다음 봉 종가/기준 종가 여유 {confirmation_buffer * 100:.1f}%",
    ]
    return score_result(
        breakdown,
        evidence,
        {
            "start": max(0, first_index - 80),
            "bearish": first_index,
            "bullish": second_index,
            "confirmation": i,
        },
    )


def evaluate_early_stage2(c: list[dict[str, Any]], i: int) -> dict[str, Any] | None:
    if i < 90:
        return None
    last = c[i]
    if last["volume"] <= 0 or last["ma30"] <= 0:
        return None
    prior_52_week_high_close = max(item["close"] for item in c[i - 52 : i])
    if last["close"] <= prior_52_week_high_close:
        return None
    previous_volume = c[i - 1]["volume"]
    if previous_volume <= 0:
        return None
    breakout_previous_volume_ratio = last["volume"] / previous_volume
    if breakout_previous_volume_ratio < 1.0:
        return None

    ma30_distance = last["close"] / max(1, last["ma30"]) - 1
    if ma30_distance < 0:
        return None

    ma30_slope_8 = last["ma30"] / max(1, c[i - 8]["ma30"]) - 1
    ma30_slope_4 = last["ma30"] / max(1, c[i - 4]["ma30"]) - 1
    previous_ma30_slope_4 = c[i - 4]["ma30"] / max(1, c[i - 8]["ma30"]) - 1
    if ma30_slope_8 < -0.03 and ma30_slope_4 < 0:
        return None

    consecutive_above_ma30 = 0
    for candle in reversed(c[: i + 1]):
        if candle["close"] > candle["ma30"]:
            consecutive_above_ma30 += 1
        else:
            break
    if consecutive_above_ma30 >= 20:
        return None

    four_week_gain = last["close"] / max(1, c[i - 4]["close"]) - 1
    if four_week_gain > 0.40 and ma30_distance > 0.35:
        return None

    best: dict[str, Any] | None = None
    seen_base_starts: set[int] = set()
    for base_weeks in range(20, min(80, i - 8) + 1):
        search_start = i - base_weeks + 1
        resistance_cluster = early_stage2_resistance_cluster(c, search_start, i)
        if resistance_cluster is None:
            continue

        start = min(resistance_cluster)
        if start in seen_base_starts:
            continue
        seen_base_starts.add(start)

        base_weeks = i - start + 1
        if not 20 <= base_weeks <= 80:
            continue

        base = c[start : i + 1]
        if len(base) != base_weeks or any(item["volume"] <= 0 for item in base):
            continue

        prior = c[max(0, start - 16) : start]
        if len(prior) < 8:
            continue

        closes = [item["close"] for item in base]
        base_high = max(closes)
        base_low = min(closes)
        base_depth = (base_high - base_low) / max(1, base_high)
        if base_depth > 0.50:
            continue

        prior_decline = max(item["close"] for item in prior) / max(1, c[start]["close"]) - 1
        if prior_decline < 0.08 and base_weeks < 28:
            continue

        resistance = early_stage2_projected_resistance(c, resistance_cluster, i)
        if resistance <= 0:
            continue
        breakout_rate = last["close"] / max(1, resistance) - 1
        if breakout_rate <= 0:
            continue

        volume_window = c[max(0, i - 10) : i]
        volume_average = avg(item["volume"] for item in volume_window)
        volume_ratio = last["volume"] / max(1, volume_average)

        recent_10_gain = last["close"] / max(1, c[i - 10]["close"]) - 1
        ma30_10_gain = last["ma30"] / max(1, c[i - 10]["ma30"]) - 1
        recent_20_low = min(item["low"] for item in c[i - 19 : i + 1])
        previous_20_low = min(item["low"] for item in c[i - 39 : i - 19])
        below_recent = sum(1 for item in c[i - 9 : i + 1] if item["close"] < item["ma30"])
        below_previous = sum(1 for item in c[i - 19 : i - 9] if item["close"] < item["ma30"])
        relative_strength_hits = sum(
            [
                recent_10_gain > ma30_10_gain,
                recent_20_low > previous_20_low,
                below_recent < below_previous,
            ]
        )

        breakdown = {
            "ma30_recovery": 20 if ma30_distance <= 0.08 else 15 if ma30_distance <= 0.15 else 8,
            "ma30_slope": 20 if ma30_slope_8 >= 0 and ma30_slope_4 >= 0 else 15 if ma30_slope_8 >= -0.03 and ma30_slope_4 >= 0 else 10 if ma30_slope_4 > previous_ma30_slope_4 else 0,
            "base_quality": early_stage2_base_quality_score(base_weeks, base_depth),
            "base_breakout": 15 if breakout_rate >= 0.03 else 12,
            "volume_confirmation": 10 if volume_ratio >= 2.0 else 8 if volume_ratio >= 1.5 else 6 if volume_ratio >= 1.3 else 3 if volume_ratio >= 1.0 else 0,
            "relative_strength": 10 if relative_strength_hits == 3 else 7 if relative_strength_hits == 2 else 4 if relative_strength_hits == 1 else 0,
            "overheat_control": 5 if four_week_gain <= 0.25 and ma30_distance <= 0.20 else 2,
        }
        if breakdown["base_quality"] <= 0:
            continue

        evidence = [
            f"MA30주 회복, 이격도 {ma30_distance * 100:.1f}%",
            f"MA30주 8주/4주 기울기 {ma30_slope_8 * 100:.1f}% / {ma30_slope_4 * 100:.1f}%",
            f"베이스 {base_weeks}주, 종가 기준 낙폭 {base_depth * 100:.1f}%",
            f"베이스 상단 돌파율 {breakout_rate * 100:.1f}%",
            f"돌파봉 거래량/전주 거래량 {breakout_previous_volume_ratio * 100:.1f}%",
            f"거래량/최근 10주 평균 {volume_ratio * 100:.1f}%",
            f"상대강도 대체 조건 {relative_strength_hits}/3개 충족",
            f"최근 4주 상승률 {four_week_gain * 100:.1f}%",
            f"MA30주 위 연속 {consecutive_above_ma30}주",
        ]
        result = score_result(
            breakdown,
            evidence,
            {
                "start": max(0, start - 12),
                "base_start": start,
                "base_resistance_indices": resistance_cluster,
            },
        )
        if best is None or result["score"] > best["score"]:
            best = result

    return best


def early_stage2_base_quality_score(base_weeks: int, base_depth: float) -> int:
    if base_depth > 0.50:
        return 0
    if base_weeks >= 60:
        return 20
    if base_weeks >= 45:
        return 17
    if base_weeks >= 30:
        return 14
    if base_weeks >= 20:
        return 10
    return 0


def early_stage2_resistance_cluster(c: list[dict[str, Any]], start: int, end: int) -> list[int] | None:
    local_highs = [
        index
        for index in range(start, end)
        if is_local_high(c, index, start, end - 1)
    ]
    if len(local_highs) < 2:
        return None

    best_cluster: list[int] | None = None
    for anchor in local_highs:
        anchor_close = c[anchor]["close"]
        cluster = [
            index
            for index in local_highs
            if 0.90 <= c[index]["close"] / max(1, anchor_close) <= 1.10
        ]
        if len(cluster) < 2:
            continue
        if best_cluster is None:
            best_cluster = cluster
            continue
        current_key = (max(c[index]["high"] for index in cluster), len(cluster), -min(cluster))
        best_key = (max(c[index]["high"] for index in best_cluster), len(best_cluster), -min(best_cluster))
        if current_key > best_key:
            best_cluster = cluster
    return sorted(best_cluster) if best_cluster is not None else None


def is_local_high(c: list[dict[str, Any]], index: int, start: int, end: int) -> bool:
    left = max(start, index - 5)
    right = min(end, index + 5)
    high = c[index]["high"]
    return high == max(c[near]["high"] for near in range(left, right + 1))


def early_stage2_projected_resistance(c: list[dict[str, Any]], indices: list[int], target_index: int) -> float:
    if len(indices) == 1:
        return c[indices[0]]["close"]
    count = len(indices)
    mean_x = sum(indices) / count
    mean_y = sum(c[index]["close"] for index in indices) / count
    denominator = sum((index - mean_x) ** 2 for index in indices)
    if denominator == 0:
        return mean_y
    slope = sum((index - mean_x) * (c[index]["close"] - mean_y) for index in indices) / denominator
    intercept = mean_y - slope * mean_x
    return intercept + slope * target_index


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


def build_pattern_markers(
    slug: str,
    visible: list[dict[str, Any]],
    indices: dict[str, Any],
    absolute_start: int,
) -> list[dict[str, str]]:
    markers: list[dict[str, str]] = []

    def add(absolute_index: int | None, label: str, position: str = "aboveBar", shape: str = "circle", color: str = "#facc15") -> None:
        if absolute_index is None:
            return
        relative_index = absolute_index - absolute_start
        if relative_index < 0 or relative_index >= len(visible):
            return
        markers.append(
            {
                "time": visible[relative_index]["time"],
                "label": label,
                "position": position,
                "shape": shape,
                "color": color,
            }
        )

    if slug == "pullback":
        add(indices.get("trend_high"), "고점", "aboveBar", "circle", "#facc15")
        add(indices.get("confirmation"), "확정봉", "belowBar", "arrowUp", "#22c55e")
    elif slug == "triangle":
        for count, peak_index in enumerate((indices.get("pivot_high_indices") or [])[:5], start=1):
            add(peak_index, f"고점{count}", "aboveBar", "circle", "#facc15")
        add(indices.get("pivot"), "피벗", "aboveBar", "arrowUp", "#38bdf8")
    elif slug == "flag":
        add(indices.get("surge_start"), "급등 시작", "belowBar", "circle", "#22c55e")
        add(indices.get("surge_peak"), "급등 고점", "aboveBar", "circle", "#facc15")
        add(indices.get("flag_end"), "조정 확인", "belowBar", "arrowUp", "#38bdf8")
    elif slug == "flat-base":
        add(indices.get("prior_peak"), "선행 고점", "aboveBar", "circle", "#facc15")
        add(indices.get("base_start"), "베이스 시작", "belowBar", "circle", "#38bdf8")
        add(indices.get("tight_end"), "Tight 3주", "aboveBar", "square", "#a855f7")
        add(indices.get("ma10_touch"), "MA10 근접", "belowBar", "arrowUp", "#22c55e")
    elif slug == "bullish-engulfing":
        add(indices.get("bearish"), "음봉", "belowBar", "circle", "#3b82f6")
        add(indices.get("bullish"), "양봉 장악", "belowBar", "arrowUp", "#ef4444")
        add(indices.get("confirmation"), "다음 봉", "aboveBar", "circle", "#a855f7")
    elif slug == "early-stage2":
        for count, resistance_index in enumerate((indices.get("base_resistance_indices") or [])[:5], start=1):
            add(resistance_index, f"상단{count}", "aboveBar", "circle", "#facc15")
        add(indices.get("start"), "베이스 시작", "belowBar", "circle", "#38bdf8")
        add(len(visible) - 1 + absolute_start, "돌파봉", "aboveBar", "arrowUp", "#22c55e")

    return markers


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


def wick_quality_score(tail_sum: float) -> int:
    if tail_sum <= 0.10:
        return 20
    if tail_sum <= 0.20:
        return 14
    if tail_sum <= 0.30:
        return 8
    return 0


def low_rank_in_window(candles: list[dict[str, Any]], index: int, before: int, after: int) -> int:
    start = index - before
    end = index + after
    if start < 0 or end >= len(candles):
        return 999
    target_low = candles[index]["low"]
    lower_count = sum(1 for candle in candles[start : end + 1] if candle["low"] < target_low)
    return lower_count + 1


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
            f"    {sql_json(item['breakdown'])}::jsonb,\n"
            f"    {sql_json(item.get('pattern_markers', []))}::jsonb\n"
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
        "  ) AS rq(id, symbol, source_symbol, source_exchange, source_url, source_date_range, difficulty, base_date, chart_data, actual_next_candles, correct_answer, ai_explanation, rule_score, pattern_evidence, pattern_score_breakdown, pattern_markers)\n"
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
        "  pattern_markers,\n"
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
        "  rq.pattern_markers,\n"
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
        "  pattern_markers = EXCLUDED.pattern_markers,\n"
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
