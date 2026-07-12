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
      ('20000000-0000-0000-0000-000000000008'::uuid, 'flat-base', 'SAMPLE-FLAT', 'hard'::question_difficulty, 'bull'::market_regime, '2024-07-02'::date, 'up'::answer_direction, '선행 상승 이후 주봉 종가가 15% 이내 조정 범위에서 좁게 움직이며 플랫베이스 압축을 형성했습니다.', 85.0, 0.5800),
      ('20000000-0000-0000-0000-000000000009'::uuid, 'bullish-engulfing', 'SAMPLE-ENGULF', 'medium'::question_difficulty, 'sideways'::market_regime, '2024-07-03'::date, 'up'::answer_direction, '52주 고점 대비 충분히 내려온 위치에서 음봉 뒤 양봉이 몸통을 완전히 감싸며 상승장악형을 완성했습니다.', 82.0, 0.6400),
      ('20000000-0000-0000-0000-000000000010'::uuid, 'volume-spike', 'SAMPLE-VOL', 'medium'::question_difficulty, 'volatile'::market_regime, '2024-07-04'::date, 'down'::answer_direction, '거래량 급증 후 윗꼬리가 길게 남아 단기 차익실현 압력이 우세한 모습입니다.', 77.0, 0.5200)
  ) AS sq(id, pattern_slug, symbol, difficulty, market_regime, base_date, correct_answer, ai_explanation, rule_score, public_accuracy)
),
sample_chart AS (
  SELECT
    '[
      {"time":"2024-04-04","open":85.2,"high":86.8,"low":84.4,"close":86.1,"volume":720000,"ma20":87.4},
      {"time":"2024-04-05","open":86.0,"high":87.1,"low":84.9,"close":85.3,"volume":760000,"ma20":87.1},
      {"time":"2024-04-08","open":85.4,"high":88.0,"low":85.1,"close":87.6,"volume":830000,"ma20":86.9},
      {"time":"2024-04-09","open":87.5,"high":88.4,"low":86.2,"close":86.8,"volume":790000,"ma20":86.8},
      {"time":"2024-04-10","open":86.7,"high":87.2,"low":83.9,"close":84.6,"volume":940000,"ma20":86.5},
      {"time":"2024-04-11","open":84.7,"high":85.9,"low":82.8,"close":83.4,"volume":1010000,"ma20":86.1},
      {"time":"2024-04-12","open":83.5,"high":85.0,"low":82.9,"close":84.4,"volume":890000,"ma20":85.8},
      {"time":"2024-04-15","open":84.5,"high":86.6,"low":84.0,"close":86.0,"volume":810000,"ma20":85.5},
      {"time":"2024-04-16","open":86.1,"high":88.9,"low":85.7,"close":88.2,"volume":1030000,"ma20":85.4},
      {"time":"2024-04-17","open":88.1,"high":89.3,"low":86.4,"close":87.0,"volume":970000,"ma20":85.3},
      {"time":"2024-04-18","open":87.1,"high":87.8,"low":85.0,"close":85.8,"volume":900000,"ma20":85.2},
      {"time":"2024-04-19","open":85.7,"high":86.9,"low":84.2,"close":84.9,"volume":860000,"ma20":85.1},
      {"time":"2024-04-22","open":85.0,"high":86.4,"low":83.8,"close":86.1,"volume":780000,"ma20":85.1},
      {"time":"2024-04-23","open":86.0,"high":88.1,"low":85.4,"close":87.6,"volume":870000,"ma20":85.2},
      {"time":"2024-04-24","open":87.7,"high":90.2,"low":87.1,"close":89.4,"volume":1090000,"ma20":85.5},
      {"time":"2024-04-25","open":89.3,"high":91.0,"low":88.0,"close":90.6,"volume":1160000,"ma20":85.9},
      {"time":"2024-04-26","open":90.5,"high":92.0,"low":89.4,"close":91.5,"volume":1240000,"ma20":86.4},
      {"time":"2024-04-29","open":91.6,"high":93.1,"low":90.8,"close":92.4,"volume":1320000,"ma20":87.0},
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
  public_accuracy,
  pattern_evidence
)
SELECT
  sq.id,
  p.id,
  sq.symbol,
  'US',
  CASE
    WHEN p.slug IN ('cup-and-handle', 'triangle', 'flag', 'flat-base') THEN '1w'
    ELSE '1d'
  END,
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
  sq.public_accuracy,
  CASE sq.pattern_slug
    WHEN 'cup-and-handle' THEN '["초반부에서 둥근 바닥 형태로 가격이 회복됩니다.", "전고점 부근에서 짧은 눌림 구간이 만들어졌습니다.", "손잡이 이후 이동평균선 위에서 재상승을 시도합니다."]'::jsonb
    WHEN 'double-bottom' THEN '["비슷한 가격대에서 두 번의 저점이 확인됩니다.", "두 번째 저점이 첫 저점보다 크게 낮아지지 않았습니다.", "중간 반등 고점 neckline 회복을 시도합니다."]'::jsonb
    WHEN 'box-breakout' THEN '["수평 저항선 부근에서 여러 번 막힌 흔적이 있습니다.", "박스권 상단을 종가 기준으로 벗어나는 흐름입니다.", "돌파 구간에서 거래량이 함께 증가합니다."]'::jsonb
    WHEN 'new-high-breakout' THEN '["이전 고점 매물대를 다시 테스트합니다.", "고점 근처에서 가격이 밀리지 않고 버티는 흐름입니다.", "돌파 시도 구간에서 추세 추종 흐름이 강해집니다."]'::jsonb
    WHEN 'pullback' THEN '["기존 상승 추세가 먼저 형성되어 있습니다.", "단기 조정이 이동평균선 근처에서 멈춥니다.", "눌림 이후 다시 양봉 반등이 나타납니다."]'::jsonb
    WHEN 'triangle' THEN '["고점과 저점의 변동폭이 점점 줄어듭니다.", "수렴 구간 끝으로 갈수록 방향성이 압축됩니다.", "아직 명확한 돌파가 나오지 않아 다음 방향 확인이 필요합니다."]'::jsonb
    WHEN 'flag' THEN '["강한 추세 이동 뒤 짧은 조정 채널이 이어집니다.", "조정 폭이 이전 추세에 비해 작습니다.", "채널 상단 돌파 여부가 다음 흐름의 핵심입니다."]'::jsonb
    WHEN 'flat-base' THEN '["선행 상승 이후 깊게 무너지지 않고 쉬어가는 구간입니다.", "주간 종가 기준 3주 변동폭이 1.5% 이내로 압축됩니다.", "10/30/40주 이동평균선과 함께 베이스 품질을 확인합니다."]'::jsonb
    WHEN 'bullish-engulfing' THEN '["첫째 날 음봉 뒤 둘째 날 양봉이 몸통을 장악합니다.", "52주 최고 종가 대비 충분히 하락한 위치에서 나온 반전 신호입니다.", "패턴 완성 후 10거래일 동안 기준 종가를 이탈하지 않았습니다."]'::jsonb
    ELSE '["평균 대비 거래량이 눈에 띄게 증가했습니다.", "거래량 급증 구간에서 캔들 꼬리와 종가 위치가 중요합니다.", "다음 봉에서 거래량 발생 구간을 지키는지 확인해야 합니다."]'::jsonb
  END
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
  pattern_evidence = EXCLUDED.pattern_evidence,
  is_active = true,
  updated_at = now();
