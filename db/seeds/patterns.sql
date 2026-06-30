INSERT INTO patterns (id, slug, name, sort_order) VALUES
  ('10000000-0000-0000-0000-000000000001', 'cup-and-handle', '컵앤핸들', 1),
  ('10000000-0000-0000-0000-000000000002', 'double-bottom', 'W바닥', 2),
  ('10000000-0000-0000-0000-000000000003', 'box-breakout', '박스권 돌파', 3),
  ('10000000-0000-0000-0000-000000000004', 'new-high-breakout', '신고가 돌파', 4),
  ('10000000-0000-0000-0000-000000000005', 'pullback', '눌림목', 5),
  ('10000000-0000-0000-0000-000000000006', 'triangle', '삼각수렴', 6),
  ('10000000-0000-0000-0000-000000000007', 'flag', '플래그', 7),
  ('10000000-0000-0000-0000-000000000008', 'inverse-head-shoulders', '역헤드앤숄더', 8),
  ('10000000-0000-0000-0000-000000000009', 'moving-average-breakout', '이동평균선 돌파', 9),
  ('10000000-0000-0000-0000-000000000010', 'volume-spike', '거래량 급증', 10)
ON CONFLICT (slug) DO UPDATE SET
  name = EXCLUDED.name,
  sort_order = EXCLUDED.sort_order,
  is_active = true,
  updated_at = now();
