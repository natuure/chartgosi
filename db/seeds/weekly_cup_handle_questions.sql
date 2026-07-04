WITH cup_questions AS (
  SELECT *
  FROM (
    VALUES
      ('21000000-0000-0000-0000-000000000001'::uuid, 'CUP-WEEKLY-01', 'medium'::question_difficulty, 'bull'::market_regime, '2026-01-02'::date, 0.0, 92.0, 0.7400, 13, 2),
      ('21000000-0000-0000-0000-000000000002'::uuid, 'CUP-WEEKLY-02', 'medium'::question_difficulty, 'bull'::market_regime, '2026-01-09'::date, 2.4, 89.0, 0.7100, 12, 1),
      ('21000000-0000-0000-0000-000000000003'::uuid, 'CUP-WEEKLY-03', 'hard'::question_difficulty, 'sideways'::market_regime, '2026-01-16'::date, -1.8, 86.0, 0.6800, 14, 2),
      ('21000000-0000-0000-0000-000000000004'::uuid, 'CUP-WEEKLY-04', 'medium'::question_difficulty, 'bull'::market_regime, '2026-01-23'::date, 5.0, 91.0, 0.7300, 13, 3),
      ('21000000-0000-0000-0000-000000000005'::uuid, 'CUP-WEEKLY-05', 'hard'::question_difficulty, 'volatile'::market_regime, '2026-01-30'::date, -4.0, 84.0, 0.6600, 15, 2),
      ('21000000-0000-0000-0000-000000000006'::uuid, 'CUP-WEEKLY-06', 'medium'::question_difficulty, 'bull'::market_regime, '2026-02-06'::date, 8.5, 88.0, 0.7000, 12, 1),
      ('21000000-0000-0000-0000-000000000007'::uuid, 'CUP-WEEKLY-07', 'hard'::question_difficulty, 'sideways'::market_regime, '2026-02-13'::date, 1.2, 83.0, 0.6400, 14, 3),
      ('21000000-0000-0000-0000-000000000008'::uuid, 'CUP-WEEKLY-08', 'medium'::question_difficulty, 'bull'::market_regime, '2026-02-20'::date, 11.0, 90.0, 0.7200, 13, 2),
      ('21000000-0000-0000-0000-000000000009'::uuid, 'CUP-WEEKLY-09', 'hard'::question_difficulty, 'volatile'::market_regime, '2026-02-27'::date, -6.5, 85.0, 0.6700, 15, 1),
      ('21000000-0000-0000-0000-000000000010'::uuid, 'CUP-WEEKLY-10', 'medium'::question_difficulty, 'bull'::market_regime, '2026-03-06'::date, 4.2, 93.0, 0.7600, 12, 2)
  ) AS cq(id, symbol, difficulty, market_regime, base_date, price_offset, rule_score, public_accuracy, bottom_week, volume_penalty_weeks)
),
base_chart AS (
  SELECT
    cq.*,
    gs AS candle_index,
    (cq.base_date - ((29 - gs) * INTERVAL '7 days'))::date AS candle_date,
    CASE
      WHEN gs <= 4 THEN 100 + cq.price_offset + gs * 8.25
      WHEN gs <= 12 THEN 133 + cq.price_offset - (gs - 4) * 2.9
      WHEN gs <= 17 THEN 108.9 + cq.price_offset + POWER(gs - cq.bottom_week, 2) * 0.42
      WHEN gs <= 24 THEN 110.2 + cq.price_offset + (gs - 17) * 3.05
      ELSE 131.6 + cq.price_offset - (gs - 24) * 1.55
    END AS close_value,
    CASE
      WHEN gs <= 4 THEN 2500000 + gs * 180000
      WHEN gs <= 12 THEN 1500000 - (gs - 5) * 65000
      WHEN gs <= 17 THEN 930000 + ABS(gs - cq.bottom_week) * 35000
      WHEN gs <= 24 THEN 1120000 + (gs - 17) * 90000
      ELSE 1180000 - (gs - 24) * 45000
    END AS base_volume
  FROM cup_questions cq
  CROSS JOIN generate_series(0, 29) AS gs
),
chart_ohlc AS (
  SELECT
    *,
    CASE
      WHEN candle_index IN (6, 7, 8, 9, 10, 11, 12, 25, 26, 27, 28) THEN close_value * 1.018
      ELSE close_value * 0.982
    END AS open_value
  FROM base_chart
),
chart_candles AS (
  SELECT
    id,
    jsonb_agg(
      jsonb_build_object(
        'time', candle_date::text,
        'open', round(open_value::numeric, 2),
        'high', round((GREATEST(open_value, close_value) * 1.028)::numeric, 2),
        'low', round((LEAST(open_value, close_value) * 0.972)::numeric, 2),
        'close', round(close_value::numeric, 2),
        'volume', (base_volume + CASE WHEN candle_index IN (26, 27) AND volume_penalty_weeks >= 2 THEN 180000 ELSE 0 END)::int,
        'ma20', round((close_value * 0.965 + candle_index * 0.07)::numeric, 2)
      )
      ORDER BY candle_index
    ) AS chart_data
  FROM chart_ohlc
  GROUP BY id
),
next_base AS (
  SELECT
    cq.*,
    gs AS candle_index,
    (cq.base_date + ((gs + 1) * INTERVAL '7 days'))::date AS candle_date,
    125.4 + cq.price_offset + gs * 4.15 AS close_value,
    1300000 + gs * 220000 AS base_volume
  FROM cup_questions cq
  CROSS JOIN generate_series(0, 4) AS gs
),
next_ohlc AS (
  SELECT
    *,
    CASE WHEN candle_index = 1 THEN close_value * 1.01 ELSE close_value * 0.975 END AS open_value
  FROM next_base
),
next_candles AS (
  SELECT
    id,
    jsonb_agg(
      jsonb_build_object(
        'time', candle_date::text,
        'open', round(open_value::numeric, 2),
        'high', round((GREATEST(open_value, close_value) * 1.032)::numeric, 2),
        'low', round((LEAST(open_value, close_value) * 0.978)::numeric, 2),
        'close', round(close_value::numeric, 2),
        'volume', base_volume::int,
        'ma20', round((close_value * 0.955)::numeric, 2)
      )
      ORDER BY candle_index
    ) AS actual_next_candles
  FROM next_ohlc
  GROUP BY id
),
pattern_row AS (
  SELECT id
  FROM patterns
  WHERE slug = 'cup-and-handle'
  LIMIT 1
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
  pattern_evidence
)
SELECT
  cq.id,
  p.id,
  cq.symbol,
  'US',
  '1w',
  cq.difficulty,
  cq.market_regime,
  cq.base_date,
  cc.chart_data,
  nc.actual_next_candles,
  'up'::answer_direction,
  '주봉 기준 5봉 이내 30% 이상 급등한 뒤, 거래량이 줄어든 완만한 U자형 컵과 얕은 핸들이 이어진 구간입니다. 오른쪽 림이 왼쪽 림의 90~105% 범위에 있고 핸들 낙폭이 컵 낙폭보다 작아, 컵앤핸들 스코어보드상 상승 돌파 가능성이 높은 문제로 분류했습니다.',
  cq.rule_score,
  cq.public_accuracy,
  jsonb_build_array(
    '주봉 5봉 이내 30% 이상 급등 이후 패턴이 시작됩니다.',
    '컵 구간은 최소 4주 이상이며 고점 대비 낙폭이 30% 이내입니다.',
    '컵 형성 중 거래량이 급등 구간보다 말라 있고, 상승 주의 거래량 우위가 유지됩니다.',
    '오른쪽 림은 왼쪽 림 대비 90~105% 범위이며 핸들 낙폭은 20% 이내입니다.'
  )
FROM cup_questions cq
CROSS JOIN pattern_row p
JOIN chart_candles cc ON cc.id = cq.id
JOIN next_candles nc ON nc.id = cq.id
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
  is_active = true,
  updated_at = now();
