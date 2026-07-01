INSERT INTO users (
  id,
  email,
  password_hash,
  nickname,
  plan,
  daily_question_limit,
  streak_days
) VALUES (
  '00000000-0000-0000-0000-000000000001',
  'dev@chartgosi.local',
  NULL,
  '개발 사용자',
  'free',
  10,
  7
)
ON CONFLICT (email) DO UPDATE SET
  nickname = EXCLUDED.nickname,
  plan = EXCLUDED.plan,
  daily_question_limit = EXCLUDED.daily_question_limit,
  streak_days = EXCLUDED.streak_days,
  updated_at = now();

INSERT INTO subscriptions (
  id,
  user_id,
  plan,
  status,
  provider
) VALUES (
  '40000000-0000-0000-0000-000000000001',
  '00000000-0000-0000-0000-000000000001',
  'free',
  'active',
  'internal'
)
ON CONFLICT (id) DO UPDATE SET
  plan = EXCLUDED.plan,
  status = EXCLUDED.status,
  provider = EXCLUDED.provider,
  updated_at = now();
