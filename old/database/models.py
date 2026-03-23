from __future__ import annotations
from typing import TYPE_CHECKING

from .db import get_db

if TYPE_CHECKING:
    from asyncpg import Record


async def create_bracket(
    guild_id: int, channel_id: int, creator_id: int, title: str
) -> int:
    """Create a new bracket and return its ID."""
    pool = await get_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO brackets (guild_id, channel_id, creator_id, title) VALUES ($1, $2, $3, $4) RETURNING id",
            guild_id, channel_id, creator_id, title,
        )
        if row is None:
            raise RuntimeError("Failed to insert bracket")
        return row["id"]


async def get_bracket(bracket_id: int) -> Record | None:
    """Get bracket by ID."""
    pool = await get_db()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM brackets WHERE id = $1", bracket_id)


async def get_active_bracket(channel_id: int) -> Record | None:
    """Get the active bracket for a channel."""
    pool = await get_db()
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM brackets WHERE channel_id = $1 AND phase != 'completed' ORDER BY id DESC LIMIT 1",
            channel_id,
        )


async def update_bracket(bracket_id: int, **kwargs):
    """Update bracket fields."""
    pool = await get_db()
    async with pool.acquire() as conn:
        fields = ", ".join(f"{k} = ${i+1}" for i, k in enumerate(kwargs.keys()))
        values = list(kwargs.values()) + [bracket_id]
        await conn.execute(f"UPDATE brackets SET {fields} WHERE id = ${len(kwargs) + 1}", *values)


async def add_contestant(bracket_id: int, name: str, submitted_by: int) -> int:
    """Add a contestant to a bracket."""
    pool = await get_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO contestants (bracket_id, name, submitted_by) VALUES ($1, $2, $3) RETURNING id",
            bracket_id, name, submitted_by,
        )
        if row is None:
            raise RuntimeError("Failed to insert contestant")
        return row["id"]


async def get_contestants(
    bracket_id: int, include_eliminated: bool = False
) -> list[Record]:
    """Get all contestants for a bracket."""
    pool = await get_db()
    async with pool.acquire() as conn:
        query = "SELECT * FROM contestants WHERE bracket_id = $1"
        if not include_eliminated:
            query += " AND eliminated_in_round IS NULL"
        query += " ORDER BY created_at"
        rows = await conn.fetch(query, bracket_id)
        return list(rows)


async def update_contestants(bracket_id: int, names: list[str], submitted_by: int):
    """Replace all contestants for a bracket."""
    pool = await get_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Delete existing contestants
            await conn.execute("DELETE FROM contestants WHERE bracket_id = $1", bracket_id)
            # Add new contestants
            for name in names:
                await conn.execute(
                    "INSERT INTO contestants (bracket_id, name, submitted_by) VALUES ($1, $2, $3)",
                    bracket_id, name.strip(), submitted_by,
                )


async def eliminate_contestant(contestant_id: int, round_number: int):
    """Mark a contestant as eliminated in a specific round."""
    pool = await get_db()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE contestants SET eliminated_in_round = $1 WHERE id = $2",
            round_number, contestant_id,
        )


async def create_match(
    bracket_id: int,
    round_number: int,
    match_number: int,
    contestant_1_id: int | None,
    contestant_2_id: int | None,
    is_play_in: bool = False,
) -> int:
    """Create a new match."""
    pool = await get_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO matches (bracket_id, round_number, match_number,
               contestant_1_id, contestant_2_id, is_play_in)
               VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
            bracket_id,
            round_number,
            match_number,
            contestant_1_id,
            contestant_2_id,
            is_play_in,
        )
        if row is None:
            raise RuntimeError("Failed to insert match")
        return row["id"]


async def get_round_matches(bracket_id: int, round_number: int) -> list[Record]:
    """Get all matches for a specific round."""
    pool = await get_db()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM matches WHERE bracket_id = $1 AND round_number = $2 ORDER BY match_number",
            bracket_id, round_number,
        )
        return list(rows)


async def get_match(match_id: int) -> Record | None:
    """Get a match by ID."""
    pool = await get_db()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM matches WHERE id = $1", match_id)


async def update_match(match_id: int, **kwargs):
    """Update match fields."""
    pool = await get_db()
    async with pool.acquire() as conn:
        fields = ", ".join(f"{k} = ${i+1}" for i, k in enumerate(kwargs.keys()))
        values = list(kwargs.values()) + [match_id]
        await conn.execute(f"UPDATE matches SET {fields} WHERE id = ${len(kwargs) + 1}", *values)


async def add_vote(match_id: int, user_id: int, contestant_id: int) -> bool:
    """Add a vote for a contestant in a match. Returns True if successful, False if duplicate."""
    pool = await get_db()
    async with pool.acquire() as conn:
        try:
            await conn.execute(
                "INSERT INTO votes (match_id, user_id, contestant_id) VALUES ($1, $2, $3)",
                match_id, user_id, contestant_id,
            )
            return True
        except Exception:
            return False


async def update_vote(match_id: int, user_id: int, contestant_id: int) -> bool:
    """Update an existing vote. Returns True if successful."""
    pool = await get_db()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE votes SET contestant_id = $1 WHERE match_id = $2 AND user_id = $3",
            contestant_id, match_id, user_id,
        )
        # Parse the result string "UPDATE N" to get row count
        return int(result.split()[-1]) > 0


async def get_user_vote(match_id: int, user_id: int) -> Record | None:
    """Get a user's vote for a specific match."""
    pool = await get_db()
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM votes WHERE match_id = $1 AND user_id = $2",
            match_id, user_id,
        )


async def get_vote_counts(match_id: int) -> dict[int, int]:
    """Get vote counts for each contestant in a match."""
    pool = await get_db()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT contestant_id, COUNT(*) as count FROM votes WHERE match_id = $1 GROUP BY contestant_id",
            match_id,
        )
        return {row["contestant_id"]: row["count"] for row in rows}


async def get_contestant(contestant_id: int) -> Record | None:
    """Get a contestant by ID."""
    pool = await get_db()
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM contestants WHERE id = $1", contestant_id
        )
