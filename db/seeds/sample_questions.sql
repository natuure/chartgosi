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
  '20000000-0000-0000-0000-000000000001',
  patterns.id,
  'SAMPLE',
  'US',
  '1d',
  'medium',
  'sideways',
  '2024-06-21',
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
  ]'::jsonb,
  '[
    {"time":"2024-05-17","open":100.3,"high":103.8,"low":99.6,"close":103.1,"volume":2100000,"ma20":96.1},
    {"time":"2024-05-20","open":103.0,"high":105.2,"low":101.9,"close":104.4,"volume":2300000,"ma20":96.8},
    {"time":"2024-05-21","open":104.5,"high":107.6,"low":103.8,"close":106.9,"volume":2450000,"ma20":97.6},
    {"time":"2024-05-22","open":106.8,"high":108.4,"low":105.1,"close":105.8,"volume":1980000,"ma20":98.2},
    {"time":"2024-05-23","open":105.9,"high":109.8,"low":105.5,"close":109.1,"volume":2550000,"ma20":99.1}
  ]'::jsonb,
  'up',
  '컵앤핸들 이후 손잡이 구간에서 가격이 이동평균선 위를 지키고, 돌파 구간에서 거래량이 증가했습니다.',
  87.5,
  0.7000
FROM patterns
WHERE patterns.slug = 'cup-and-handle'
ON CONFLICT (id) DO UPDATE SET
  pattern_id = EXCLUDED.pattern_id,
  chart_data = EXCLUDED.chart_data,
  actual_next_candles = EXCLUDED.actual_next_candles,
  correct_answer = EXCLUDED.correct_answer,
  ai_explanation = EXCLUDED.ai_explanation,
  public_accuracy = EXCLUDED.public_accuracy,
  is_active = true,
  updated_at = now();
