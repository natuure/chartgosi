import asyncio
import sys
from pathlib import Path
from typing import Iterable

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool


BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
SEED_DIR = ROOT_DIR / "db" / "seeds"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from scripts.init_db import split_sql  # noqa: E402


QUESTION_SEED_FILES = [
    "patterns.sql",
    "remaining_pattern_scorecards.sql",
    "real_cup_handle_questions.sql",
    "real_double_bottom_questions.sql",
    "real_box_breakout_questions.sql",
    "real_new_high_breakout_questions.sql",
    "real_pullback_questions.sql",
    "real_triangle_questions.sql",
    "real_flag_questions.sql",
    "real_flat_base_questions.sql",
    "real_bullish_engulfing_questions.sql",
    "real_early_stage2_questions.sql",
    "zz_disable_volume_spike.sql",
]


async def main() -> None:
    engine_kwargs = {
        "connect_args": settings.asyncpg_connect_args,
    }
    if settings.uses_external_pooler:
        engine_kwargs["poolclass"] = NullPool

    engine = create_async_engine(settings.sqlalchemy_database_url, **engine_kwargs)
    try:
        async with engine.begin() as connection:
            for seed_name in question_seed_files():
                seed_path = SEED_DIR / seed_name
                await execute_sql_file(connection, seed_path)
                print(f"applied={seed_path}")
    finally:
        await engine.dispose()


def question_seed_files() -> Iterable[str]:
    selected = [arg for arg in sys.argv[1:] if arg.endswith(".sql")]
    return selected or QUESTION_SEED_FILES


async def execute_sql_file(connection, file_path: Path) -> None:
    sql = file_path.read_text(encoding="utf-8").replace("\ufeff", "")
    for statement in split_sql(sql):
        await connection.exec_driver_sql(statement)


if __name__ == "__main__":
    asyncio.run(main())
