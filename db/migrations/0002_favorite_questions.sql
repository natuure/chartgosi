CREATE TABLE IF NOT EXISTS favorite_questions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  question_id uuid NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_favorite_questions_user_question UNIQUE (user_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_favorite_questions_user_created
  ON favorite_questions(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_favorite_questions_question
  ON favorite_questions(question_id);
