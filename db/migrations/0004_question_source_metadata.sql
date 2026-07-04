ALTER TABLE questions
  ADD COLUMN IF NOT EXISTS is_synthetic boolean NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS source_name text,
  ADD COLUMN IF NOT EXISTS source_url text,
  ADD COLUMN IF NOT EXISTS source_symbol varchar(40),
  ADD COLUMN IF NOT EXISTS source_exchange varchar(40),
  ADD COLUMN IF NOT EXISTS source_date_range text,
  ADD COLUMN IF NOT EXISTS pattern_score_breakdown jsonb;

CREATE INDEX IF NOT EXISTS idx_questions_real_source
  ON questions(is_synthetic, source_symbol, base_date DESC);
