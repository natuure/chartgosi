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
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_SQL = ROOT_DIR / "db" / "seeds" / "real_box_breakout_questions.sql"
OUTPUT_JSON = ROOT_DIR / "data" / "real_box_breakout_candidates.json"
NAVER_MARKET_URL = "https://finance.naver.com/sise/sise_market_sum.naver"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

NEXT_FIVE_UP_THRESHOLD = 0.10
NEXT_FIVE_DOWN_THRESHOLD = -0.10
TARGET_ANSWER_COUNTS = {"up": 5, "sideways": 2, "down": 3}
QUESTION_ANSWER_ORDER = ["up", "down", "up", "sideways", "up", "down", "up", "sideways", "up", "down"]

MIN_BOX_DAYS = 15
MAX_BOX_DAYS = 80
BOX_DAY_CANDIDATES = (15, 20, 25, 30, 40, 50, 60, 80)
MAX_BOX_WIDTH = 0.45
GOOD_BOX_WIDTH = 0.35
MIN_BREAKOUT_RATE = 0.03
OVERHEATED_BREAKOUT_RATE = 0.15
MIN_BREAKOUT_VOLUME_RATIO = 1.00
RESISTANCE_TOUCH_BAND = 0.03
SUPPORT_TOUCH_BAND = 0.03
MIN_RESISTANCE_TOUCH_GROUPS = 2
MIN_SCORE = 75
PAGES_PER_MARKET = 8
MAX_WORKERS = 16

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")


@dataclass(frozen=True)
class ListedStock:
    code: str
    name: str
    market: str
    yahoo_symbol: str


def main() -> None:
    stocks = load_listed_stocks(pages_per_market=PAGES_PER_MARKET)
    print(f"listed_candidates={len(stocks)}", flush=True)

    scored: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(scan_stock, stock): stock for stock in stocks}
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
        "ETF",
        "ETN",
        "스팩",
        "SPAC",
    )
    return any(keyword in name for keyword in fund_keywords)


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


def scan_stock(stock: ListedStock) -> list[dict[str, Any]]:
    candles = fetch_daily_candles(stock.yahoo_symbol)
    if len(candles) < MAX_BOX_DAYS + 10:
        return []

    best_by_answer: dict[str, dict[str, Any]] = {}
    for breakout_index in range(MIN_BOX_DAYS, len(candles) - 5):
        for box_days in BOX_DAY_CANDIDATES:
            if box_days > breakout_index:
                continue
            box_start = breakout_index - box_days
            score_result = evaluate_box_breakout_candidate(candles, box_start, breakout_index)
            if score_result is None or score_result["score"] < MIN_SCORE:
                continue

            visible = candles[box_start : breakout_index + 1]
            future = candles[breakout_index + 1 : breakout_index + 6]
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
                "chart_data": visible,
                "actual_next_candles": future,
                "correct_answer": answer,
                "next_five_return": round(next_five_return, 4),
            }
            current = best_by_answer.get(answer)
            if current is None or (result["score"], result["base_date"]) > (current["score"], current["base_date"]):
                best_by_answer[answer] = result
    return list(best_by_answer.values())


def fetch_daily_candles(symbol: str) -> list[dict[str, Any]]:
    period2 = int(datetime.now(UTC).timestamp())
    period1 = int((datetime.now(UTC) - timedelta(days=365 * 4)).timestamp())
    query = urllib.parse.urlencode(
        {
            "period1": period1,
            "period2": period2,
            "interval": "1d",
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
        candles.append(
            {
                "time": datetime.fromtimestamp(timestamp, UTC).date().isoformat(),
                "open": round(float(opens[index]), 2),
                "high": round(float(highs[index]), 2),
                "low": round(float(lows[index]), 2),
                "close": round(float(closes[index]), 2),
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


def evaluate_box_breakout_candidate(candles: list[dict[str, Any]], box_start: int, breakout_index: int) -> dict[str, Any] | None:
    box = candles[box_start:breakout_index]
    breakout = candles[breakout_index]
    if len(box) < MIN_BOX_DAYS or len(box) > MAX_BOX_DAYS:
        return None

    closes = [c["close"] for c in box]
    box_top = max(closes)
    box_bottom = min(closes)
    if box_bottom <= 0:
        return None

    box_width = box_top / box_bottom - 1
    if box_width > MAX_BOX_WIDTH:
        return None

    resistance_indices = [index for index, candle in enumerate(box) if candle["close"] >= box_top * (1 - RESISTANCE_TOUCH_BAND)]
    resistance_groups = count_touch_groups(resistance_indices)
    if resistance_groups < MIN_RESISTANCE_TOUCH_GROUPS:
        return None

    support_indices = [index for index, candle in enumerate(box) if candle["close"] <= box_bottom * (1 + SUPPORT_TOUCH_BAND)]
    support_groups = count_touch_groups(support_indices)
    if support_groups < 2:
        return None

    breakout_rate = breakout["close"] / box_top - 1
    if breakout_rate < MIN_BREAKOUT_RATE:
        return None

    prior_volumes = [c["volume"] for c in candles[max(0, breakout_index - 20) : breakout_index]]
    if len(prior_volumes) < 10:
        return None
    avg_prior_volume = sum(prior_volumes) / len(prior_volumes)
    breakout_volume_ratio = breakout["volume"] / max(1, avg_prior_volume)
    if breakout_volume_ratio < MIN_BREAKOUT_VOLUME_RATIO:
        return None

    candle_range = max(1, breakout["high"] - breakout["low"])
    upper_wick_start = breakout["close"] if breakout["close"] >= breakout["open"] else breakout["open"]
    upper_wick_ratio = (breakout["high"] - upper_wick_start) / candle_range
    close_position = (breakout["close"] - breakout["low"]) / candle_range

    breakdown: dict[str, float] = {}
    box_days = len(box)
    breakdown["box_duration"] = 10 if 25 <= box_days <= 60 else 8
    breakdown["box_width_stability"] = 15 if box_width <= 0.25 else 10 if box_width <= GOOD_BOX_WIDTH else 5
    breakdown["resistance_touches"] = 15 if resistance_groups >= 3 else 12
    breakdown["support_touches"] = 10 if support_groups >= 3 else 8

    close_inside_ratio = sum(1 for candle in box if box_bottom <= candle["close"] <= box_top) / len(box)
    breakdown["inside_close_control"] = 10 if close_inside_ratio >= 0.95 else 7 if close_inside_ratio >= 0.9 else 4
    breakdown["breakout_strength"] = score_breakout_strength(breakout_rate)
    breakdown["breakout_volume"] = score_breakout_volume(breakout_volume_ratio)
    breakdown["close_quality"] = 5 if upper_wick_ratio <= 0.25 and close_position >= 0.65 else 3 if upper_wick_ratio <= 0.4 else 0

    ma50 = float(breakout.get("ma50") or 0)
    previous_ma50 = float(candles[breakout_index - 5].get("ma50") or 0) if breakout_index >= 5 else ma50
    breakdown["ma_recovery"] = 5 if breakout["close"] >= ma50 and ma50 >= previous_ma50 * 0.98 else 3 if breakout["close"] >= ma50 else 0

    score = sum(breakdown.values())
    evidence = [
        f"박스 형성 {box_days}거래일",
        f"박스 폭 {box_width * 100:.1f}%",
        f"상단 저항 확인 {resistance_groups}회",
        f"하단 지지 확인 {support_groups}회",
        f"돌파율 {breakout_rate * 100:.1f}%",
        f"돌파 거래량/20일 평균 {breakout_volume_ratio * 100:.1f}%",
        f"돌파 봉 윗꼬리 비율 {upper_wick_ratio * 100:.1f}%",
    ]
    indices = {
        "box_start": box_start,
        "breakout": breakout_index,
    }
    return {"score": score, "breakdown": breakdown, "evidence": evidence, "indices": indices}


def count_touch_groups(indices: list[int], min_gap: int = 5) -> int:
    if not indices:
        return 0
    groups = 1
    previous = indices[0]
    for index in indices[1:]:
        if index - previous >= min_gap:
            groups += 1
        previous = index
    return groups


def score_breakout_strength(breakout_rate: float) -> int:
    if breakout_rate >= 0.10:
        return 15
    if breakout_rate >= 0.08:
        return 13
    if breakout_rate >= 0.05:
        return 10
    if breakout_rate >= 0.03:
        return 7
    return 0


def score_breakout_volume(volume_ratio: float) -> int:
    if volume_ratio >= 2.00:
        return 15
    if volume_ratio >= 1.50:
        return 12
    if volume_ratio >= 1.30:
        return 9
    if volume_ratio >= 1.00:
        return 6
    return 0


def classify_next_five(last_visible: dict[str, Any], future: list[dict[str, Any]]) -> str:
    move = future[-1]["close"] / last_visible["close"] - 1
    if move >= NEXT_FIVE_UP_THRESHOLD:
        return "up"
    if move <= NEXT_FIVE_DOWN_THRESHOLD:
        return "down"
    return "sideways"


def select_balanced_questions(scored: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected_by_answer: dict[str, list[dict[str, Any]]] = {answer: [] for answer in TARGET_ANSWER_COUNTS}
    used_codes: set[str] = set()

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

        selected = max(candidates, key=lambda item: (item["score"], item["base_date"]))
        selected_by_answer[answer].append(selected)
        used_codes.add(selected["stock"]["code"])

    ordered: list[dict[str, Any]] = []
    cursor = {answer: 0 for answer in TARGET_ANSWER_COUNTS}
    for answer in QUESTION_ANSWER_ORDER:
        ordered.append(selected_by_answer[answer][cursor[answer]])
        cursor[answer] += 1
    return ordered


def write_outputs(selected: list[dict[str, Any]]) -> None:
    OUTPUT_JSON.parent.mkdir(exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")

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
            f"{stock['name']}({stock['code']})의 실제 일봉 데이터에서 박스권 돌파 스코어 "
            f"{item['score']:.1f}점을 통과한 구간입니다. 박스 형성 기간, 상단 저항 확인, "
            f"종가 기준 돌파 강도, 돌파 거래량 조건을 기준으로 선별했습니다. "
            f"실제 다음 5봉 종가 기준 등락률은 {item['next_five_return'] * 100:.1f}%로, 정답은 {answer_label}입니다."
        )
        values.append(
            "\n  (\n"
            f"    '25000000-0000-0000-0000-{index:012d}'::uuid,\n"
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
        "  WHERE slug = 'box-breakout'\n"
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
        "  '1d',\n"
        "  rq.difficulty,\n"
        "  'sideways'::market_regime,\n"
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
    OUTPUT_SQL.write_text(sql, encoding="utf-8")


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_json(value: Any) -> str:
    return sql_quote(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
