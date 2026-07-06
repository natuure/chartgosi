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
OUTPUT_SQL = ROOT_DIR / "db" / "seeds" / "real_double_bottom_questions.sql"
OUTPUT_JSON = ROOT_DIR / "data" / "real_double_bottom_candidates.json"
NAVER_MARKET_URL = "https://finance.naver.com/sise/sise_market_sum.naver"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

NEXT_FIVE_UP_THRESHOLD = 0.10
NEXT_FIVE_DOWN_THRESHOLD = -0.10
TARGET_ANSWER_COUNTS = {"up": 5, "sideways": 2, "down": 3}
QUESTION_ANSWER_ORDER = ["up", "down", "up", "sideways", "up", "down", "up", "sideways", "up", "down"]

PRE_DROP_LOOKBACK_DAYS = 20
MIN_PRE_DROP = 0.20
MIN_BOTTOM_GAP_DAYS = 10
MAX_BOTTOM_GAP_DAYS = 30
BOTTOM_RATIO_MIN = 0.95
BOTTOM_RATIO_MAX = 1.05
MIN_NECKLINE_BOUNCE = 0.10
SECOND_BOTTOM_RECOVERY = 0.05
MIN_SCORE = 75
MAX_PATTERN_CANDLES = PRE_DROP_LOOKBACK_DAYS + MAX_BOTTOM_GAP_DAYS + 45
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
    if len(candles) < 90:
        return []

    best_by_answer: dict[str, dict[str, Any]] = {}
    for score_result in find_double_bottom_candidates(candles):
        if score_result["score"] < MIN_SCORE:
            continue

        indices = score_result["indices"]
        recovery_index = indices["recovery"]
        pattern_start = max(0, indices["first_bottom"] - PRE_DROP_LOOKBACK_DAYS)
        visible = candles[pattern_start : recovery_index + 1]
        future = candles[recovery_index + 1 : recovery_index + 6]
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


def find_double_bottom_candidates(candles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    closes = [c["close"] for c in candles]
    if len(candles) < PRE_DROP_LOOKBACK_DAYS + MIN_BOTTOM_GAP_DAYS + 2:
        return []

    candidates: list[dict[str, Any]] = []
    latest_second_bottom = len(candles) - 6
    for first_bottom in range(PRE_DROP_LOOKBACK_DAYS, latest_second_bottom - MIN_BOTTOM_GAP_DAYS + 1):
        pre_high = max(closes[first_bottom - PRE_DROP_LOOKBACK_DAYS : first_bottom])
        pre_drop = closes[first_bottom] / pre_high - 1
        if pre_drop > -MIN_PRE_DROP:
            continue
        second_start = first_bottom + MIN_BOTTOM_GAP_DAYS
        second_end = min(first_bottom + MAX_BOTTOM_GAP_DAYS, latest_second_bottom)
        for second_bottom in range(second_start, second_end + 1):
            recovery_index = find_first_recovery_index(closes, second_bottom)
            if recovery_index is None or recovery_index > len(candles) - 6:
                continue
            candidate = evaluate_double_bottom_candidate(candles, first_bottom, second_bottom, recovery_index)
            if candidate is None:
                continue
            candidates.append(candidate)
    return candidates


def score_double_bottom(candles: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = find_double_bottom_candidates(candles)
    if not candidates:
        return empty_score()
    return max(candidates, key=lambda candidate: candidate["score"])


def find_first_recovery_index(closes: list[float], second_bottom: int) -> int | None:
    target = closes[second_bottom] * (1 + SECOND_BOTTOM_RECOVERY)
    for index in range(second_bottom + 1, len(closes)):
        if closes[index] >= target:
            return index
    return None


def evaluate_double_bottom_candidate(
    candles: list[dict[str, Any]],
    first_bottom: int,
    second_bottom: int,
    recovery_index: int,
) -> dict[str, Any] | None:
    closes = [c["close"] for c in candles]
    first_close = closes[first_bottom]
    second_close = closes[second_bottom]
    gap_days = second_bottom - first_bottom
    if gap_days < MIN_BOTTOM_GAP_DAYS or gap_days > MAX_BOTTOM_GAP_DAYS:
        return None

    pre_high = max(closes[first_bottom - PRE_DROP_LOOKBACK_DAYS : first_bottom])
    pre_drop = first_close / pre_high - 1
    if pre_drop > -MIN_PRE_DROP:
        return None

    bottom_ratio = second_close / first_close
    if bottom_ratio < BOTTOM_RATIO_MIN or bottom_ratio > BOTTOM_RATIO_MAX:
        return None

    neckline = max(range(first_bottom + 1, second_bottom), key=lambda index: closes[index])
    neckline_close = closes[neckline]
    neckline_bounce = neckline_close / first_close - 1
    if neckline_bounce < MIN_NECKLINE_BOUNCE:
        return None

    recovery_ratio = closes[recovery_index] / second_close - 1
    if recovery_ratio < SECOND_BOTTOM_RECOVERY:
        return None

    breakdown: dict[str, float] = {}
    breakdown["prior_downtrend"] = 15
    breakdown["bottom_similarity"] = 20 if 0.97 <= bottom_ratio <= 1.03 else 16
    breakdown["neckline_bounce"] = 15 if neckline_bounce >= 0.15 else 10
    breakdown["bottom_spacing"] = 10 if 14 <= gap_days <= 24 else 8
    breakdown["second_bottom_recovery"] = 15 if recovery_ratio >= 0.08 else 12

    first_volume = candles[first_bottom]["volume"]
    second_volume = candles[second_bottom]["volume"]
    volume_ratio = second_volume / max(1, first_volume)
    breakdown["second_bottom_volume_stability"] = 10 if volume_ratio <= 1.10 else 7 if volume_ratio <= 1.50 else 4 if volume_ratio <= 2 else 0

    recent_volumes = [c["volume"] for c in candles[max(0, recovery_index - 5) : recovery_index]]
    recent_avg_volume = sum(recent_volumes) / len(recent_volumes) if recent_volumes else candles[recovery_index]["volume"]
    recovery_volume_ratio = candles[recovery_index]["volume"] / max(1, recent_avg_volume)
    breakdown["recovery_volume"] = 10 if recovery_volume_ratio >= 1 else 6 if recovery_volume_ratio >= 0.8 else 2

    ma20 = float(candles[recovery_index].get("ma20") or 0)
    breakdown["short_trend_recovery"] = 5 if closes[recovery_index] >= ma20 else 3 if closes[recovery_index] >= ma20 * 0.97 else 0

    score = sum(breakdown.values())
    evidence = [
        f"20거래일 선행 하락률 {abs(pre_drop) * 100:.1f}%",
        f"두 저점 종가 비율 {bottom_ratio * 100:.1f}%",
        f"neckline 반등률 {neckline_bounce * 100:.1f}%",
        f"두 저점 간격 {gap_days}거래일",
        f"2차 저점 이후 회복률 {recovery_ratio * 100:.1f}%",
        f"2차 저점 거래량/1차 저점 거래량 {volume_ratio * 100:.1f}%",
        f"회복 봉 거래량/최근 5일 평균 {recovery_volume_ratio * 100:.1f}%",
    ]
    indices = {
        "first_bottom": first_bottom,
        "neckline": neckline,
        "second_bottom": second_bottom,
        "recovery": recovery_index,
    }
    return {"score": score, "breakdown": breakdown, "evidence": evidence, "indices": indices}


def empty_score() -> dict[str, Any]:
    return {"score": 0, "breakdown": {}, "evidence": []}


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
            f"{stock['name']}({stock['code']})의 실제 일봉 데이터에서 W바닥 스코어 "
            f"{item['score']:.1f}점을 통과한 구간입니다. 20거래일 선행 하락, 두 저점 유사성, "
            f"neckline 반등, 2차 저점 이후 5% 회복 조건을 기준으로 선별했습니다. "
            f"실제 다음 5봉 종가 기준 등락률은 {item['next_five_return'] * 100:.1f}%로, 정답은 {answer_label}입니다."
        )
        values.append(
            "\n  (\n"
            f"    '24000000-0000-0000-0000-{index:012d}'::uuid,\n"
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
        "  WHERE slug = 'double-bottom'\n"
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
        "  'volatile'::market_regime,\n"
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
