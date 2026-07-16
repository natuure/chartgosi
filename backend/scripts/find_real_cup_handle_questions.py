import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_SQL = ROOT_DIR / "db" / "seeds" / "real_cup_handle_questions.sql"
OUTPUT_JSON = ROOT_DIR / "data" / "real_cup_handle_candidates.json"
NAVER_MARKET_URL = "https://finance.naver.com/sise/sise_market_sum.naver"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}
NEXT_FIVE_UP_THRESHOLD = 0.10
NEXT_FIVE_DOWN_THRESHOLD = -0.10
TARGET_ANSWER_COUNTS = {"up": 15, "sideways": 6, "down": 9}
QUESTION_ANSWER_ORDER = [
    "up", "down", "up", "sideways", "up", "down", "up", "sideways", "up", "down",
    "up", "down", "up", "sideways", "up", "down", "up", "sideways", "up", "down",
    "up", "down", "up", "sideways", "up", "down", "up", "sideways", "up", "down",
]
TARGET_HANDLE_WEEK_COUNTS = {1: 6, 2: 6, 3: 7, 4: 6, 5: 5}
QUESTION_ID_OFFSET = 1000
MAX_WORKERS = 32
FETCH_TIMEOUT_SECONDS = 6
REQUIRED_HANDLE_WEEKS = (3, 4, 5)
HANDLE_NEAR_CUP_BOTTOM_BUFFER = 0.05
HANDLE_NEAR_CUP_BOTTOM_PENALTY = 5
HANDLE_MIN_RIGHT_RIM_RECOVERY = 0.95
MIN_CUP_WEEKS = 4
MAX_CUP_WEEKS = 52
HANDLE_MIN_WEEKS = 1
HANDLE_MAX_WEEKS = 5
MAX_PATTERN_CANDLES = 1 + 5 + MAX_CUP_WEEKS + HANDLE_MAX_WEEKS

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")


@dataclass(frozen=True)
class ListedStock:
    code: str
    name: str
    market: str
    yahoo_symbol: str


def main() -> None:
    candidates = load_listed_stocks(pages_per_market=16)
    print(f"listed_candidates={len(candidates)}", flush=True)

    scored: list[dict[str, Any]] = []
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    futures = {}
    try:
        futures = {executor.submit(scan_stock, stock): stock for stock in candidates}
        for index, future in enumerate(as_completed(futures), start=1):
            stock = futures[future]
            try:
                results = future.result()
                if results:
                    scored.extend(results)
                    summary = ", ".join(f"{item['correct_answer']}={item['score']:.1f}" for item in results)
                    print(f"pass {len(scored):02d}: {stock.code} {stock.name} {summary}", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"skip {stock.code} {stock.name}: {exc}", flush=True)
            if index % 100 == 0:
                print(f"scanned={index} passed={len(scored)}", flush=True)
            if has_selectable_questions(scored):
                print(f"balanced_candidates_ready_at={index}", flush=True)
                break
    finally:
        for future in futures:
            future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)

    selected = select_balanced_questions(scored)
    selected_counts = {answer: sum(1 for item in selected if item["correct_answer"] == answer) for answer in TARGET_ANSWER_COUNTS}
    print(f"selected_counts={selected_counts}", flush=True)

    write_outputs(selected)
    print(f"wrote_sql={OUTPUT_SQL}", flush=True)
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
    fund_keywords = (
        "KODEX",
        "TIGER",
        "ACE",
        "RISE",
        "SOL ",
        "PLUS",
        "TIME",
        "UNICORN",
        "KOSEF",
        "KBSTAR",
        "HANARO",
        "ARIRANG",
        "히어로즈",
        "마이티",
        "ETF",
        "ETN",
        "스팩",
        "SPAC",
    )
    return any(keyword in name for keyword in fund_keywords)


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


def scan_stock(stock: ListedStock) -> list[dict[str, Any]]:
    candles = fetch_weekly_candles(stock.yahoo_symbol)
    if len(candles) < 80:
        return []

    best_by_answer_and_handle: dict[tuple[str, int], dict[str, Any]] = {}
    for handle_end_index in range(11, len(candles) - 5):
        window_start = max(0, handle_end_index - MAX_PATTERN_CANDLES + 1)
        candidate = candles[window_start : handle_end_index + 1]
        score_result = score_cup_and_handle(candidate)
        if score_result["score"] < 80:
            continue
        indices = score_result["indices"]
        pattern_start = window_start + indices["surge_start"]
        handle_end = window_start + indices["handle_end"]
        handle_weeks = indices["handle_end"] - indices["right_rim"]
        visible = candles[pattern_start : handle_end + 1]
        future = candles[handle_end + 1 : handle_end + 6]
        if len(future) < 5:
            continue
        answer = classify_next_five(visible[-1], future)
        next_five_return = future[-1]["close"] / visible[-1]["close"] - 1

        result = {
            "stock": stock.__dict__,
            "score": round(score_result["score"], 2),
            "breakdown": score_result["breakdown"],
            "evidence": score_result["evidence"],
            "base_date": visible[-1]["time"],
            "handle_weeks": handle_weeks,
            "chart_data": visible,
            "pattern_markers": build_pattern_markers(
                visible,
                {
                    "surge_start": window_start + indices["surge_start"],
                    "left_rim": window_start + indices["left_rim"],
                    "bottom": window_start + indices["bottom"],
                    "right_rim": window_start + indices["right_rim"],
                    "handle_end": handle_end,
                },
                pattern_start,
            ),
            "actual_next_candles": future,
            "correct_answer": answer,
            "next_five_return": round(next_five_return, 4),
        }
        current = best_by_answer_and_handle.get((answer, handle_weeks))
        if current is None or (result["score"], result["base_date"]) > (current["score"], current["base_date"]):
            best_by_answer_and_handle[(answer, handle_weeks)] = result
    return list(best_by_answer_and_handle.values())


def select_balanced_questions(scored: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected_by_answer: dict[str, list[dict[str, Any]]] = {answer: [] for answer in TARGET_ANSWER_COUNTS}
    used_codes: set[str] = set()
    handle_counts = {weeks: 0 for weeks in TARGET_HANDLE_WEEK_COUNTS}

    for answer in QUESTION_ANSWER_ORDER:
        candidates = [
            item
            for item in scored
            if item["correct_answer"] == answer
            and item["stock"]["code"] not in used_codes
            and len(selected_by_answer[answer]) < TARGET_ANSWER_COUNTS[answer]
        ]
        if not candidates:
            raise RuntimeError(f"Need more {answer} questions")

        def selection_key(item: dict[str, Any]) -> tuple[int, int, int, float, str]:
            handle_weeks = item["handle_weeks"]
            required_bonus = 1 if handle_weeks in REQUIRED_HANDLE_WEEKS and handle_counts.get(handle_weeks, 0) == 0 else 0
            target_bonus = 1 if handle_counts.get(handle_weeks, 0) < TARGET_HANDLE_WEEK_COUNTS.get(handle_weeks, 0) else 0
            long_handle_bonus = 1 if handle_weeks >= 3 else 0
            return (required_bonus, target_bonus, long_handle_bonus, item["score"], item["base_date"])

        selected = max(candidates, key=selection_key)
        selected_by_answer[answer].append(selected)
        used_codes.add(selected["stock"]["code"])
        handle_counts[selected["handle_weeks"]] = handle_counts.get(selected["handle_weeks"], 0) + 1

    missing_handle_weeks = [weeks for weeks in REQUIRED_HANDLE_WEEKS if handle_counts.get(weeks, 0) == 0]
    if missing_handle_weeks:
        raise RuntimeError(f"Missing required handle week buckets: {missing_handle_weeks}")

    ordered: list[dict[str, Any]] = []
    cursor = {answer: 0 for answer in TARGET_ANSWER_COUNTS}
    for answer in QUESTION_ANSWER_ORDER:
        ordered.append(selected_by_answer[answer][cursor[answer]])
        cursor[answer] += 1
    return ordered


def has_selectable_questions(scored: list[dict[str, Any]]) -> bool:
    try:
        selected = select_balanced_questions(scored)
    except RuntimeError:
        return False
    return len(selected) == sum(TARGET_ANSWER_COUNTS.values())


def fetch_weekly_candles(symbol: str) -> list[dict[str, Any]]:
    period2 = int(datetime.now(UTC).timestamp())
    period1 = int((datetime.now(UTC) - timedelta(days=365 * 10)).timestamp())
    query = urllib.parse.urlencode(
        {
            "period1": period1,
            "period2": period2,
            "interval": "1wk",
            "events": "history",
            "includeAdjustedClose": "true",
        }
    )
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
        close = float(closes[index])
        candles.append(
            {
                "time": datetime.fromtimestamp(timestamp, UTC).date().isoformat(),
                "open": round(float(opens[index]), 2),
                "high": round(float(highs[index]), 2),
                "low": round(float(lows[index]), 2),
                "close": round(close, 2),
                "volume": int(volumes[index]),
                "ma10": 0,
                "ma20": 0,
                "ma30": 0,
                "ma40": 0,
                "ma50": 0,
                "ma150": 0,
                "ma200": 0,
            }
        )

    closes_for_ma: list[float] = []
    for candle in candles:
        closes_for_ma.append(candle["close"])
        for period in (10, 20, 30, 40, 50, 150, 200):
            lookback = closes_for_ma[-period:]
            candle[f"ma{period}"] = round(sum(lookback) / len(lookback), 2)

    return candles


def score_cup_and_handle(candles: list[dict[str, Any]]) -> dict[str, Any]:
    closes = [c["close"] for c in candles]
    if len(candles) < 12:
        return empty_score()

    handle_end_index = len(candles) - 1
    best: dict[str, Any] | None = None
    for surge_start, surge_end, surge_gain in find_initial_surges(closes, handle_end_index):
        right_search_start = surge_start + MIN_CUP_WEEKS
        right_search_end = min(surge_end + MAX_CUP_WEEKS, handle_end_index - HANDLE_MIN_WEEKS)
        for right_rim in range(right_search_start, right_search_end + 1):
            candidate = evaluate_cup_and_handle_candidate(
                candles,
                surge_start,
                surge_end,
                surge_gain,
                right_rim,
                handle_end_index,
            )
            if candidate is None:
                continue
            if best is None or candidate["score"] > best["score"]:
                best = candidate
    return best or empty_score()


def evaluate_cup_and_handle_candidate(
    candles: list[dict[str, Any]],
    surge_start: int,
    surge_end: int,
    surge_gain: float,
    right_rim: int,
    handle_end: int,
) -> dict[str, Any] | None:
    closes = [c["close"] for c in candles]
    left_rim = max(range(surge_start, surge_end + 1), key=lambda index: (closes[index], -index))
    cup_start = left_rim + 1
    left_rim_close = closes[left_rim]
    right_rim_close = closes[right_rim]

    cup_weeks = right_rim - left_rim
    if cup_weeks < MIN_CUP_WEEKS or cup_weeks > MAX_CUP_WEEKS:
        return None
    if cup_start >= right_rim:
        return None
    if any(close > left_rim_close for close in closes[cup_start:right_rim]):
        return None

    bottom = min(range(cup_start, right_rim), key=lambda index: closes[index])
    bottom_close = closes[bottom]
    cup_range = candles[cup_start : right_rim + 1]
    handle = candles[right_rim + 1 : handle_end + 1]
    handle_weeks = len(handle)
    if handle_weeks < HANDLE_MIN_WEEKS or handle_weeks > HANDLE_MAX_WEEKS:
        return None
    if any(c["close"] > right_rim_close for c in handle):
        return None
    recovery_close = right_rim_close * HANDLE_MIN_RIGHT_RIM_RECOVERY
    if any(c["close"] >= recovery_close for c in handle[:-1]):
        return None
    handle_recovery_ratio = handle[-1]["close"] / right_rim_close
    if handle_recovery_ratio < HANDLE_MIN_RIGHT_RIM_RECOVERY:
        return None
    if not has_weekly_ma_bullish_alignment(candles[handle_end]):
        return None

    cup_bottom_low = min(c["low"] for c in cup_range)
    handle_low = min(c["low"] for c in handle)
    if handle_low < cup_bottom_low:
        return None

    cup_depth = (left_rim_close - bottom_close) / left_rim_close
    handle_depth = max(0, (right_rim_close - handle_low) / right_rim_close)
    rim_ratio = right_rim_close / left_rim_close
    handle_near_cup_bottom = handle_low <= bottom_close * (1 + HANDLE_NEAR_CUP_BOTTOM_BUFFER)

    surge_range = candles[surge_start : surge_end + 1]
    pattern_range = candles[cup_start : handle_end + 1]

    breakdown: dict[str, float] = {}
    breakdown["weekly_surge"] = 15 if surge_gain >= 0.30 else max(0, surge_gain / 0.30 * 15)
    breakdown["cup_duration_and_shape"] = score_cup_shape(left_rim, bottom, right_rim)
    breakdown["cup_depth_limit"] = 15 if 0.08 <= cup_depth <= 0.30 else 8 if cup_depth <= 0.34 else 0
    breakdown["cup_volume_dry_up"] = 15 if avg_volume(cup_range) <= avg_volume(surge_range) * 0.72 else 9 if avg_volume(cup_range) <= avg_volume(surge_range) * 0.85 else 0
    breakdown["up_week_volume_dominance"] = score_up_volume_dominance(pattern_range)
    down_penalty_count = count_down_volume_penalties(candles[cup_start:])
    breakdown["down_week_volume_control"] = max(0, 5 - down_penalty_count * 0.5)
    breakdown["rim_symmetry"] = 10 if 0.95 <= rim_ratio <= 1.05 else 6 if 0.90 <= rim_ratio <= 1.10 else 0
    handle_quality = 15 if handle_depth <= 0.20 and handle_depth < cup_depth else 8 if handle_depth <= 0.24 else 0
    if handle_near_cup_bottom:
        handle_quality = max(0, handle_quality - HANDLE_NEAR_CUP_BOTTOM_PENALTY)
    breakdown["handle_quality"] = handle_quality

    score = sum(breakdown.values())
    evidence = [
        f"5주 이내 급등률 {surge_gain * 100:.1f}%",
        f"컵 낙폭 {cup_depth * 100:.1f}%, 컵 형성 {cup_weeks}주",
        f"오른쪽 림 종가/왼쪽 림 종가 비율 {rim_ratio * 100:.1f}%",
        f"핸들 형성 {handle_weeks}주, 핸들 낙폭 {handle_depth * 100:.1f}%",
        f"핸들 종가 회복률 {handle_recovery_ratio * 100:.1f}%",
        f"핸들 저가가 컵 바닥 저가보다 {(handle_low / cup_bottom_low - 1) * 100:.1f}% 위",
        f"하락 주 거래량 5주 평균 상회 {down_penalty_count}회",
    ]
    indices = {
        "surge_start": surge_start,
        "surge_end": surge_end,
        "left_rim": left_rim,
        "cup_start": cup_start,
        "bottom": bottom,
        "right_rim": right_rim,
        "handle_end": handle_end,
    }
    return {"score": score, "breakdown": breakdown, "evidence": evidence, "indices": indices}


def empty_score() -> dict[str, Any]:
    return {"score": 0, "breakdown": {}, "evidence": []}


def find_initial_surges(closes: list[float], handle_end_index: int) -> list[tuple[int, int, float]]:
    surges: list[tuple[int, int, float]] = []
    latest_start = handle_end_index - MIN_CUP_WEEKS - HANDLE_MIN_WEEKS
    for start in range(0, max(0, latest_start) + 1):
        for end in range(start + 1, min(start + 6, latest_start + 2)):
            gain = closes[end] / closes[start] - 1
            if gain >= 0.30:
                surges.append((start, end, gain))
    return sorted(surges, key=lambda item: item[2], reverse=True)


def score_cup_shape(surge_end: int, bottom: int, right_rim: int) -> float:
    cup_weeks = right_rim - surge_end
    left_weeks = bottom - surge_end
    right_weeks = right_rim - bottom
    if cup_weeks < MIN_CUP_WEEKS or cup_weeks > MAX_CUP_WEEKS:
        return 0
    score = 6
    if left_weeks >= 2 and right_weeks >= 2:
        score += 5
    if left_weeks >= 3 and right_weeks >= 3:
        score += 4
    return min(15, score)


def has_weekly_ma_bullish_alignment(candle: dict[str, Any]) -> bool:
    ma10 = float(candle.get("ma10") or 0)
    ma30 = float(candle.get("ma30") or 0)
    ma40 = float(candle.get("ma40") or 0)
    return ma10 > ma30 > ma40


def avg_volume(candles: list[dict[str, Any]]) -> float:
    if not candles:
        return 0
    return sum(c["volume"] for c in candles) / len(candles)


def score_up_volume_dominance(candles: list[dict[str, Any]]) -> float:
    up_volumes = [c["volume"] for c in candles if c["close"] >= c["open"]]
    down_volumes = [c["volume"] for c in candles if c["close"] < c["open"]]
    if not up_volumes or not down_volumes:
        return 5
    ratio = (sum(up_volumes) / len(up_volumes)) / max(1, sum(down_volumes) / len(down_volumes))
    if ratio >= 1.15:
        return 10
    if ratio >= 1.0:
        return 7
    if ratio >= 0.9:
        return 4
    return 0


def count_down_volume_penalties(candles: list[dict[str, Any]]) -> int:
    penalties = 0
    volumes: list[int] = []
    for candle in candles:
        volumes.append(candle["volume"])
        moving_average = sum(volumes[-5:]) / len(volumes[-5:])
        if candle["close"] < candle["open"] and candle["volume"] > moving_average:
            penalties += 1
    return penalties


def classify_next_five(last_visible: dict[str, Any], future: list[dict[str, Any]]) -> str:
    move = future[-1]["close"] / last_visible["close"] - 1
    if move >= NEXT_FIVE_UP_THRESHOLD:
        return "up"
    if move <= NEXT_FIVE_DOWN_THRESHOLD:
        return "down"
    return "sideways"


def build_pattern_markers(
    visible: list[dict[str, Any]],
    indices: dict[str, int],
    absolute_start: int,
) -> list[dict[str, str]]:
    markers: list[dict[str, str]] = []

    def add(key: str, label: str, position: str, shape: str, color: str) -> None:
        relative_index = indices[key] - absolute_start
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

    add("surge_start", "급등 시작", "belowBar", "circle", "#22c55e")
    add("left_rim", "왼쪽림", "aboveBar", "circle", "#facc15")
    add("bottom", "컵 바닥", "belowBar", "circle", "#38bdf8")
    add("right_rim", "오른쪽림", "aboveBar", "circle", "#facc15")
    add("handle_end", "핸들 끝", "belowBar", "arrowUp", "#a855f7")
    return markers


def write_outputs(selected: list[dict[str, Any]]) -> None:
    OUTPUT_JSON.parent.mkdir(exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")

    values = []
    for index, item in enumerate(selected, start=1):
        stock = item["stock"]
        question_id = f"23000000-0000-0000-0000-{index + QUESTION_ID_OFFSET:012d}"
        symbol = sql_string(f"{stock['code']} {stock['name']}")
        source_symbol = sql_string(stock["yahoo_symbol"])
        source_exchange = sql_string(stock["market"])
        source_url = sql_string(f"https://finance.yahoo.com/quote/{stock['yahoo_symbol']}")
        source_date_range = sql_string(f"{item['chart_data'][0]['time']} ~ {item['actual_next_candles'][-1]['time']}")
        difficulty = "hard" if item["score"] < 86 else "medium"
        answer_label = {"up": "상승", "sideways": "횡보", "down": "하락"}[item["correct_answer"]]
        next_five_return = item["next_five_return"] * 100
        explanation = sql_string(
            f"{stock['name']}({stock['code']})의 실제 주봉 데이터에서 컵앤핸들 스코어 {item['score']:.1f}점을 통과한 구간입니다. "
            "5주 이내 급등 이후 완만한 컵, 거래량 감소, 림 대칭, 얕은 핸들 조건을 기준으로 선별했습니다. "
            f"실제 다음 5봉 종가 기준 등락률은 {next_five_return:.1f}%로, 정답은 {answer_label}입니다."
        )
        values.append(
            f"""(
    '{question_id}'::uuid,
    {symbol},
    {source_symbol},
    {source_exchange},
    {source_url},
    {source_date_range},
    '{difficulty}'::question_difficulty,
    '{item['base_date']}'::date,
    '{json.dumps(item['chart_data'], ensure_ascii=False)}'::jsonb,
    '{json.dumps(item['actual_next_candles'], ensure_ascii=False)}'::jsonb,
    '{item['correct_answer']}'::answer_direction,
    {explanation},
    {item['score']:.2f},
    '{json.dumps(item['evidence'], ensure_ascii=False)}'::jsonb,
    '{json.dumps(item['breakdown'], ensure_ascii=False)}'::jsonb,
    '{json.dumps(item.get('pattern_markers', []), ensure_ascii=False)}'::jsonb
  )"""
        )

    sql = f"""WITH pattern_row AS (
  SELECT id
  FROM patterns
  WHERE slug = 'cup-and-handle'
  LIMIT 1
),
real_questions AS (
  SELECT *
  FROM (
    VALUES
  {','.join(values)}
  ) AS rq(
    id,
    symbol,
    source_symbol,
    source_exchange,
    source_url,
    source_date_range,
    difficulty,
    base_date,
    chart_data,
    actual_next_candles,
    correct_answer,
    ai_explanation,
    rule_score,
    pattern_evidence,
    pattern_score_breakdown,
    pattern_markers
  )
)
INSERT INTO questions (
  id,
  pattern_id,
  symbol,
  market,
  timeframe,
  difficulty,
  market_regime,
  base_date,
  chart_data,
  actual_next_candles,
  correct_answer,
  ai_explanation,
  rule_score,
  public_accuracy,
  pattern_evidence,
  pattern_score_breakdown,
  pattern_markers,
  is_synthetic,
  source_name,
  source_url,
  source_symbol,
  source_exchange,
  source_date_range
)
SELECT
  rq.id,
  p.id,
  rq.symbol,
  'KRX',
  '1w',
  rq.difficulty,
  'bull'::market_regime,
  rq.base_date,
  rq.chart_data,
  rq.actual_next_candles,
  rq.correct_answer,
  rq.ai_explanation,
  rq.rule_score,
  0.7000,
  rq.pattern_evidence,
  rq.pattern_score_breakdown,
  rq.pattern_markers,
  false,
  'Yahoo Finance chart API',
  rq.source_url,
  rq.source_symbol,
  rq.source_exchange,
  rq.source_date_range
FROM real_questions rq
CROSS JOIN pattern_row p
ON CONFLICT (id) DO UPDATE SET
  pattern_id = EXCLUDED.pattern_id,
  symbol = EXCLUDED.symbol,
  market = EXCLUDED.market,
  timeframe = EXCLUDED.timeframe,
  difficulty = EXCLUDED.difficulty,
  market_regime = EXCLUDED.market_regime,
  base_date = EXCLUDED.base_date,
  chart_data = EXCLUDED.chart_data,
  actual_next_candles = EXCLUDED.actual_next_candles,
  correct_answer = EXCLUDED.correct_answer,
  ai_explanation = EXCLUDED.ai_explanation,
  rule_score = EXCLUDED.rule_score,
  public_accuracy = EXCLUDED.public_accuracy,
  pattern_evidence = EXCLUDED.pattern_evidence,
  pattern_score_breakdown = EXCLUDED.pattern_score_breakdown,
  pattern_markers = EXCLUDED.pattern_markers,
  is_synthetic = EXCLUDED.is_synthetic,
  source_name = EXCLUDED.source_name,
  source_url = EXCLUDED.source_url,
  source_symbol = EXCLUDED.source_symbol,
  source_exchange = EXCLUDED.source_exchange,
  source_date_range = EXCLUDED.source_date_range,
  is_active = true,
  updated_at = now();
"""
    OUTPUT_SQL.write_text(sql, encoding="utf-8")


def sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


if __name__ == "__main__":
    main()
