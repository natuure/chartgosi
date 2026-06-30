CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TYPE user_plan AS ENUM ('free', 'premium', 'b2b');
CREATE TYPE subscription_status AS ENUM ('trialing', 'active', 'past_due', 'canceled', 'expired');
CREATE TYPE question_difficulty AS ENUM ('easy', 'medium', 'hard');
CREATE TYPE market_regime AS ENUM ('bull', 'sideways', 'bear', 'volatile');
CREATE TYPE answer_direction AS ENUM ('up', 'sideways', 'down');
CREATE TYPE ranking_period_type AS ENUM ('daily', 'weekly', 'monthly', 'all_time');
CREATE TYPE report_status AS ENUM ('pending', 'completed', 'failed');

CREATE TABLE users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email varchar(255) UNIQUE NOT NULL,
  password_hash text,
  nickname varchar(80) NOT NULL,
  avatar_url text,
  plan user_plan NOT NULL DEFAULT 'free',
  daily_question_limit integer NOT NULL DEFAULT 10,
  streak_days integer NOT NULL DEFAULT 0,
  last_played_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE patterns (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug varchar(80) UNIQUE NOT NULL,
  name varchar(120) NOT NULL,
  description text,
  icon_style jsonb,
  sort_order integer NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE questions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  pattern_id uuid NOT NULL REFERENCES patterns(id),
  symbol varchar(40) NOT NULL,
  market varchar(40) NOT NULL,
  timeframe varchar(20) NOT NULL DEFAULT '1d',
  difficulty question_difficulty NOT NULL,
  market_regime market_regime NOT NULL,
  base_date date NOT NULL,
  chart_data jsonb NOT NULL,
  actual_next_candles jsonb NOT NULL,
  correct_answer answer_direction NOT NULL,
  ai_explanation text,
  rule_score numeric(5,2),
  public_accuracy numeric(5,4),
  total_answers integer NOT NULL DEFAULT 0,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE user_answers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id),
  question_id uuid NOT NULL REFERENCES questions(id),
  selected_answer answer_direction NOT NULL,
  correct_answer answer_direction NOT NULL,
  is_correct boolean NOT NULL,
  confidence integer CHECK (confidence >= 0 AND confidence <= 100),
  reason_tags text[] NOT NULL DEFAULT '{}',
  answer_duration_ms integer,
  is_retry boolean NOT NULL DEFAULT false,
  viewed_ai_explanation boolean NOT NULL DEFAULT false,
  session_id uuid,
  client_meta jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ai_reports (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id),
  status report_status NOT NULL DEFAULT 'pending',
  period_start date NOT NULL,
  period_end date NOT NULL,
  answer_count integer NOT NULL,
  overall_score integer,
  percentile numeric(5,2),
  pattern_accuracy jsonb,
  trait_scores jsonb,
  summary text,
  recommendations jsonb,
  model_name varchar(80),
  error_message text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE rankings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id),
  period_type ranking_period_type NOT NULL,
  period_start date,
  score integer NOT NULL DEFAULT 0,
  accuracy numeric(5,4) NOT NULL DEFAULT 0,
  solved_count integer NOT NULL DEFAULT 0,
  correct_count integer NOT NULL DEFAULT 0,
  rank_position integer,
  streak_days integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_rankings_user_period UNIQUE (user_id, period_type, period_start)
);

CREATE TABLE subscriptions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id),
  plan user_plan NOT NULL,
  status subscription_status NOT NULL,
  provider varchar(40),
  provider_customer_id varchar(255),
  provider_subscription_id varchar(255),
  current_period_start timestamptz,
  current_period_end timestamptz,
  cancel_at_period_end boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_plan ON users(plan);
CREATE INDEX idx_patterns_slug ON patterns(slug);
CREATE INDEX idx_patterns_active_sort ON patterns(is_active, sort_order);
CREATE INDEX idx_questions_pattern_difficulty ON questions(pattern_id, difficulty);
CREATE INDEX idx_questions_active_base_date ON questions(is_active, base_date DESC);
CREATE INDEX idx_questions_market_regime ON questions(market_regime);
CREATE INDEX idx_user_answers_user_created ON user_answers(user_id, created_at DESC);
CREATE INDEX idx_user_answers_user_correct ON user_answers(user_id, is_correct, created_at DESC);
CREATE INDEX idx_user_answers_question ON user_answers(question_id);
CREATE INDEX idx_ai_reports_user_created ON ai_reports(user_id, created_at DESC);
CREATE INDEX idx_ai_reports_status ON ai_reports(status);
CREATE INDEX idx_rankings_period_score ON rankings(period_type, period_start, score DESC);
CREATE INDEX idx_rankings_user_period ON rankings(user_id, period_type, period_start);
CREATE INDEX idx_subscriptions_user_status ON subscriptions(user_id, status);
