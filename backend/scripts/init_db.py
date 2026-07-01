import asyncio
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402


MIGRATION_DIR = ROOT_DIR / "db" / "migrations"
SEED_DIR = ROOT_DIR / "db" / "seeds"


async def main() -> None:
    engine_kwargs = {
        "connect_args": settings.asyncpg_connect_args,
    }
    if settings.uses_external_pooler:
        engine_kwargs["poolclass"] = NullPool

    engine = create_async_engine(
        settings.sqlalchemy_database_url,
        **engine_kwargs,
    )
    async with engine.begin() as connection:
        initialized = await has_users_table(connection)
        for migration_file in sorted(MIGRATION_DIR.glob("*.sql")):
            if initialized and migration_file.name == "0001_init.sql":
                continue
            await execute_sql_file(connection, migration_file)

        for seed_file in sorted(SEED_DIR.glob("*.sql")):
            await execute_sql_file(connection, seed_file)

    await engine.dispose()
    print("Database initialized.")


async def has_users_table(connection) -> bool:
    result = await connection.execute(
        text(
            """
            SELECT EXISTS (
              SELECT 1
              FROM information_schema.tables
              WHERE table_schema = 'public' AND table_name = 'users'
            )
            """
        )
    )
    return bool(result.scalar_one())


async def execute_sql_file(connection, file_path: Path) -> None:
    sql = file_path.read_text(encoding="utf-8")
    for statement in split_sql(sql):
        await connection.exec_driver_sql(statement)


def split_sql(sql: str) -> list[str]:
    return [statement.strip() for statement in sql.split(";") if statement.strip()]


if __name__ == "__main__":
    asyncio.run(main())
