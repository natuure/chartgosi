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
  updated_at = now();
