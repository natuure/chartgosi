WITH seed_questions AS (
  SELECT *
  FROM (
    VALUES
      ('20000000-0000-0000-0000-000000000001'::uuid, 'cup-and-handle', 'SAMPLE-CUP', 'medium'::question_difficulty, 'sideways'::market_regime, '2024-06-21'::date, 'up'::answer_direction, '컵앤핸들 이후 손잡이 구간에서 가격이 이동평균선 위를 지키고, 돌파 구간에서 거래량이 증가했습니다.', 87.5, 0.7000),
      ('20000000-0000-0000-0000-000000000002'::uuid, 'double-bottom', 'SAMPLE-W', 'easy'::question_difficulty, 'bull'::market_regime, '2024-06-24'::date, 'up'::answer_direction, 'W바닥의 두 번째 저점이 첫 저점보다 높고 neckline 부근 거래량이 살아나 상승 가능성이 큽니다.', 82.0, 0.6200),
      ('20000000-0000-0000-0000-000000000003'::uuid, 'box-breakout', 'SAMPLE-BOX', 'medium'::question_difficulty, 'sideways'::market_regime, '2024-06-25'::date, 'up'::answer_direction, '박스권 상단을 종가로 돌파했고 이전 저항선이 지지선으로 바뀌는 흐름입니다.', 84.0, 0.6500),
      ('20000000-0000-0000-0000-000000000004'::uuid, 'new-high-breakout', 'SAMPLE-HIGH', 'hard'::question_difficulty, 'bull'::market_regime, '2024-06-26'::date, 'up'::answer_direction, '신고가 돌파 이후 매물대가 얇아지고 추세 추종 매수세가 붙기 쉬운 구간입니다.', 86.0, 0.6100),
      ('20000000-0000-0000-0000-000000000005'::uuid, 'pullback', 'SAMPLE-PULL', 'medium'::question_difficulty, 'bull'::market_regime, '2024-06-27'::date, 'up'::answer_direction, '상승 추세 중 단기 눌림이 이동평균선에서 멈추고 반등 신호가 나왔습니다.', 80.0, 0.6700),
      ('20000000-0000-0000-0000-000000000006'::uuid, 'triangle', 'SAMPLE-TRI', 'medium'::question_difficulty, 'volatile'::market_regime, '2024-06-28'::date, 'sideways'::answer_direction, '삼각수렴 끝자락이지만 아직 명확한 방향 돌파가 없어 단기 횡보 가능성이 높습니다.', 74.0, 0.5600),
      ('20000000-0000-0000-0000-000000000007'::uuid, 'flag', 'SAMPLE-FLAG', 'hard'::question_difficulty, 'bull'::market_regime, '2024-07-01'::date, 'up'::answer_direction, '급등 뒤 작은 플래그 조정이 이어졌고 상단 돌파 시 추세가 재개될 가능성이 있습니다.', 83.0, 0.6000),
      ('20000000-0000-0000-0000-000000000008'::uuid, 'inverse-head-shoulders', 'SAMPLE-IHS', 'hard'::question_difficulty, 'bear'::market_regime, '2024-07-02'::date, 'up'::answer_direction, '역헤드앤숄더 neckline 돌파가 확인되면 하락 추세 반전 가능성을 볼 수 있습니다.', 85.0, 0.5800),
      ('20000000-0000-0000-0000-000000000009'::uuid, 'moving-average-breakout', 'SAMPLE-MA', 'easy'::question_difficulty, 'sideways'::market_regime, '2024-07-03'::date, 'up'::answer_direction, '가격이 주요 이동평균선을 회복했고 단기선이 중기선을 상향 돌파하는 초입입니다.', 79.0, 0.6400),
      ('20000000-0000-0000-0000-000000000010'::uuid, 'volume-spike', 'SAMPLE-VOL', 'medium'::question_difficulty, 'volatile'::market_regime, '2024-07-04'::date, 'down'::answer_direction, '거래량 급증 후 윗꼬리가 길게 남아 단기 차익실현 압력이 우세한 모습입니다.', 77.0, 0.5200)
  ) AS sq(id, pattern_slug, symbol, difficulty, market_regime, base_date, correct_answer, ai_explanation, rule_score, public_accuracy)
),
sample_chart AS (
  SELECT
    '[
      {"time":"2024-05-01","open":92.1,"high":95.4,"low":90.8,"close":94.2,"volume":920000,"ma20":91.6},
      {"time":"2024-05-02","open":94.2,"high":95.1,"low":91.7,"close":92.4,"volume":1100000,"ma20":91.9},
      {"time":"2024-05-03","open":92.5,"high":93.2,"low":89.9,"close":90.8,"volume":980000,"ma20":92.0},
      {"time":"2024-05-06","open":91.0,"high":92.8,"low":89.4,"close":92.1,"volume":860000,"ma20":92.2},
      {"time":"2024-05-07","open":92.3,"high":95.6,"low":91.8,"close":95.1,"volume":1250000,"ma20":92.5},
      {"time":"2024-05-08","open":95.2,"high":98.0,"low":94.4,"close":97.5,"volume":1480000,"ma20":92.9},
      {"time":"2024-05-09","open":97.2,"high":99.1,"low":95.0,"close":96.0,"volume":1320000,"ma20":93.4},
      {"time":"2024-05-10","open":96.1,"high":97.3,"low":93.2,"close":94.1,"volume":1180000,"ma20":93.7},
      {"time":"2024-05-13","open":94.0,"high":95.4,"low":92.1,"close":93.2,"volume":1030000,"ma20":94.0},
      {"time":"2024-05-14","open":93.3,"high":96.2,"low":92.8,"close":95.8,"volume":1210000,"ma20":94.4},
      {"time":"2024-05-15","open":95.9,"high":99.4,"low":95.1,"close":98.7,"volume":1620000,"ma20":94.9},
      {"time":"2024-05-16","open":98.6,"high":101.0,"low":97.8,"close":100.4,"volume":1880000,"ma20":95.5}
    ]'::jsonb AS chart_data,
    '[
      {"time":"2024-05-17","open":100.3,"high":103.8,"low":99.6,"close":103.1,"volume":2100000,"ma20":96.1},
      {"time":"2024-05-20","open":103.0,"high":105.2,"low":101.9,"close":104.4,"volume":2300000,"ma20":96.8},
      {"time":"2024-05-21","open":104.5,"high":107.6,"low":103.8,"close":106.9,"volume":2450000,"ma20":97.6},
      {"time":"2024-05-22","open":106.8,"high":108.4,"low":105.1,"close":105.8,"volume":1980000,"ma20":98.2},
      {"time":"2024-05-23","open":105.9,"high":109.8,"low":105.5,"close":109.1,"volume":2550000,"ma20":99.1}
    ]'::jsonb AS up_candles,
    '[
      {"time":"2024-05-17","open":100.3,"high":101.2,"low":99.4,"close":100.6,"volume":1420000,"ma20":96.1},
      {"time":"2024-05-20","open":100.7,"high":101.5,"low":99.8,"close":100.1,"volume":1380000,"ma20":96.8},
      {"time":"2024-05-21","open":100.0,"high":101.1,"low":99.3,"close":100.4,"volume":1300000,"ma20":97.6},
      {"time":"2024-05-22","open":100.5,"high":101.4,"low":99.6,"close":99.9,"volume":1260000,"ma20":98.2},
      {"time":"2024-05-23","open":100.0,"high":101.0,"low":99.5,"close":100.3,"volume":1220000,"ma20":99.1}
    ]'::jsonb AS sideways_candles,
    '[
      {"time":"2024-05-17","open":100.3,"high":101.0,"low":97.6,"close":98.1,"volume":2210000,"ma20":96.1},
      {"time":"2024-05-20","open":98.0,"high":98.8,"low":95.9,"close":96.4,"volume":2350000,"ma20":96.8},
      {"time":"2024-05-21","open":96.5,"high":97.2,"low":94.1,"close":94.8,"volume":2420000,"ma20":97.6},
      {"time":"2024-05-22","open":94.9,"high":95.4,"low":92.8,"close":93.7,"volume":2180000,"ma20":98.2},
      {"time":"2024-05-23","open":93.8,"high":94.3,"low":91.9,"close":92.6,"volume":2050000,"ma20":99.1}
    ]'::jsonb AS down_candles
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
  public_accuracy
)
SELECT
  sq.id,
  p.id,
  sq.symbol,
  'US',
  '1d',
  sq.difficulty,
  sq.market_regime,
  sq.base_date,
  sc.chart_data,
  CASE
    WHEN sq.correct_answer = 'up' THEN sc.up_candles
    WHEN sq.correct_answer = 'sideways' THEN sc.sideways_candles
    ELSE sc.down_candles
  END,
  sq.correct_answer,
  sq.ai_explanation,
  sq.rule_score,
  sq.public_accuracy
FROM seed_questions sq
JOIN patterns p ON p.slug = sq.pattern_slug
CROSS JOIN sample_chart sc
ON CONFLICT (id) DO UPDATE SET
  pattern_id = EXCLUDED.pattern_id,
  symbol = EXCLUDED.symbol,
  difficulty = EXCLUDED.difficulty,
  market_regime = EXCLUDED.market_regime,
  base_date = EXCLUDED.base_date,
  chart_data = EXCLUDED.chart_data,
  actual_next_candles = EXCLUDED.actual_next_candles,
  correct_answer = EXCLUDED.correct_answer,
  ai_explanation = EXCLUDED.ai_explanation,
  rule_score = EXCLUDED.rule_score,
  public_accuracy = EXCLUDED.public_accuracy,
  is_active = true,
  updated_at = now();
