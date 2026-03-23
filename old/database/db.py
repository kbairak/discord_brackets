from __future__ import annotations

from typing import TYPE_CHECKING
import os
import asyncpg

if TYPE_CHECKING:
    from asyncpg import Pool

_pool: Pool | None = None


async def init_db() -> None:
    """Initialize the database connection and create tables."""
    global _pool

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL environment variable not set. "
            "Example: postgresql://postgres:postgres@localhost:5432/discord_brackets"
        )

    _pool = await asyncpg.create_pool(database_url)

    async with _pool.acquire() as conn:
        # Create tables
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS brackets (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                creator_id BIGINT NOT NULL,
                title TEXT NOT NULL,
                phase TEXT NOT NULL DEFAULT 'collection',
                current_round INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message_id BIGINT,
                round_control_message_id BIGINT
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS contestants (
                id SERIAL PRIMARY KEY,
                bracket_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                submitted_by BIGINT NOT NULL,
                eliminated_in_round INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bracket_id) REFERENCES brackets(id) ON DELETE CASCADE
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id SERIAL PRIMARY KEY,
                bracket_id INTEGER NOT NULL,
                round_number INTEGER NOT NULL,
                match_number INTEGER NOT NULL,
                contestant_1_id INTEGER,
                contestant_2_id INTEGER,
                winner_id INTEGER,
                message_id BIGINT,
                is_play_in BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (bracket_id) REFERENCES brackets(id) ON DELETE CASCADE,
                FOREIGN KEY (contestant_1_id) REFERENCES contestants(id),
                FOREIGN KEY (contestant_2_id) REFERENCES contestants(id),
                FOREIGN KEY (winner_id) REFERENCES contestants(id)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS votes (
                id SERIAL PRIMARY KEY,
                match_id INTEGER NOT NULL,
                user_id BIGINT NOT NULL,
                contestant_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE,
                FOREIGN KEY (contestant_id) REFERENCES contestants(id),
                UNIQUE(match_id, user_id)
            )
        """)

    print(f"Database initialized: {database_url}")


async def get_db() -> Pool:
    """Get the database connection pool."""
    if _pool is None:
        await init_db()
    assert _pool is not None, "Database failed to initialize"
    return _pool
