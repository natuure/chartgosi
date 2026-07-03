ALTER TABLE patterns
  ADD COLUMN IF NOT EXISTS definition jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE questions
  ADD COLUMN IF NOT EXISTS pattern_evidence jsonb NOT NULL DEFAULT '[]'::jsonb;
