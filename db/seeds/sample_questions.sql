INSERT INTO questions (
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
  patterns.id,
  'SAMPLE',
  'US',
  '1d',
  'medium',
  'sideways',
  '2024-06-21',
  '[{"time":"2024-06-17","open":100,"high":104,"low":98,"close":103,"volume":1200000,"ma20":99.5}]'::jsonb,
  '[{"time":"2024-06-24","open":103,"high":108,"low":102,"close":107,"volume":1800000,"ma20":100.8}]'::jsonb,
  'up',
  '컵앤핸들 이후 거래량 회복과 이동평균선 지지가 함께 확인됩니다.',
  87.5,
  0.7000
FROM patterns
WHERE patterns.slug = 'cup-and-handle'
ON CONFLICT DO NOTHING;
