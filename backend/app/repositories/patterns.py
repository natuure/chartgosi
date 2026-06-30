from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def list_patterns(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
              p.id::text AS id,
              p.slug,
              p.name,
              COUNT(q.id)::int AS question_count
            FROM patterns p
            LEFT JOIN questions q ON q.pattern_id = p.id AND q.is_active = true
            WHERE p.is_active = true
            GROUP BY p.id, p.slug, p.name, p.sort_order
            ORDER BY p.sort_order ASC
            """
        )
    )
    return [dict(row) for row in result.mappings().all()]
