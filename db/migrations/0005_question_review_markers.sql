ALTER TABLE questions
  ADD COLUMN IF NOT EXISTS review_status text NOT NULL DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS review_note text NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS pattern_markers jsonb NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE questions
  DROP CONSTRAINT IF EXISTS ck_questions_review_status;

ALTER TABLE questions
  ADD CONSTRAINT ck_questions_review_status
  CHECK (review_status IN ('pending', 'approved', 'needs_review', 'rejected'));

CREATE INDEX IF NOT EXISTS idx_questions_review_status
  ON questions(review_status, updated_at DESC);
