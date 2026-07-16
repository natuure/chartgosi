import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool


BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
BACKUP_DIR = ROOT_DIR / "data" / "backups"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402


async def main() -> None:
    apply = "--apply" in sys.argv
    engine_kwargs: dict[str, Any] = {"connect_args": settings.asyncpg_connect_args}
    if settings.uses_external_pooler:
        engine_kwargs["poolclass"] = NullPool

    engine = create_async_engine(settings.sqlalchemy_database_url, **engine_kwargs)
    try:
        async with engine.begin() as connection:
            rows = (
                await connection.execute(
                    text(
                        """
                        SELECT
                          q.id::text AS id,
                          p.slug AS pattern_slug,
                          q.symbol,
                          q.base_date::text AS base_date,
                          q.correct_answer::text AS correct_answer,
                          q.review_status,
                          q.is_active,
                          q.total_answers,
                          (
                            SELECT COUNT(*)
                            FROM user_answers ua
                            WHERE ua.question_id = q.id
                          )::int AS user_answer_count,
                          (
                            SELECT COUNT(*)
                            FROM favorite_questions fq
                            WHERE fq.question_id = q.id
                          )::int AS favorite_count
                        FROM questions q
                        JOIN patterns p ON p.id = q.pattern_id
                        WHERE q.review_status = 'pending'
                        ORDER BY p.sort_order, q.base_date, q.symbol
                        """
                    )
                )
            ).mappings().all()

            backup_path = write_backup([dict(row) for row in rows])
            print(f"pending_questions={len(rows)}")
            print(f"backup={backup_path}")
            print_counts(rows)

            if not apply:
                print("dry_run=true")
                print("Run with --apply to delete pending questions.")
                return

            await connection.execute(
                text(
                    """
                    DELETE FROM user_answers
                    WHERE question_id IN (
                      SELECT id FROM questions WHERE review_status = 'pending'
                    )
                    """
                )
            )
            await connection.execute(
                text(
                    """
                    DELETE FROM questions
                    WHERE review_status = 'pending'
                    """
                )
            )
            print("deleted_pending_questions=true")
    finally:
        await engine.dispose()


def write_backup(rows: list[dict[str, Any]]) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_path = BACKUP_DIR / f"pending_questions_{stamp}.json"
    backup_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return backup_path


def print_counts(rows: list[Any]) -> None:
    counts: dict[str, int] = {}
    answer_counts: dict[str, dict[str, int]] = {}
    for row in rows:
        slug = row["pattern_slug"]
        answer = row["correct_answer"]
        counts[slug] = counts.get(slug, 0) + 1
        answer_counts.setdefault(slug, {})
        answer_counts[slug][answer] = answer_counts[slug].get(answer, 0) + 1
    for slug in sorted(counts):
        print(f"{slug}: total={counts[slug]} answers={answer_counts[slug]}")


if __name__ == "__main__":
    asyncio.run(main())
