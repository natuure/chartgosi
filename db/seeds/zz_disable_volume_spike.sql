UPDATE questions
SET is_active = false,
    updated_at = now()
WHERE pattern_id = (
  SELECT id
  FROM patterns
  WHERE slug = 'volume-spike'
  LIMIT 1
);

UPDATE patterns
SET is_active = false,
    updated_at = now()
WHERE slug = 'volume-spike';
