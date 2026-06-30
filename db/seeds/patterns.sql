INSERT INTO patterns (slug, name, sort_order) VALUES
  ('cup-and-handle', '컵앤핸들', 1),
  ('double-bottom', 'W바닥', 2),
  ('box-breakout', '박스권 돌파', 3),
  ('new-high-breakout', '신고가 돌파', 4),
  ('pullback', '눌림목', 5),
  ('triangle', '삼각수렴', 6),
  ('flag', '플래그', 7),
  ('inverse-head-shoulders', '역헤드앤숄더', 8),
  ('moving-average-breakout', '이동평균선 돌파', 9),
  ('volume-spike', '거래량 급증', 10)
ON CONFLICT (slug) DO NOTHING;
