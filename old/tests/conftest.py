import pytest
import os
from pathlib import Path
import sys
from typing import TYPE_CHECKING

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import db as db_module
from database import models

if TYPE_CHECKING:
    from asyncpg import Pool


@pytest.fixture
async def test_db():
    """Create a test database connection."""
    # Use test database URL or default to the same database with test_ prefix
    test_db_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")

    if not test_db_url:
        pytest.skip("DATABASE_URL not set - cannot run tests")

    # Store original pool
    original_pool = db_module._pool

    # Reset pool to None so init_db creates a new one
    db_module._pool = None

    # Temporarily override DATABASE_URL for test
    original_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_db_url

    # Initialize the test database
    await db_module.init_db()

    # Get the pool reference
    pool_ref: Pool | None = db_module._pool

    # Clean up all tables before tests
    assert pool_ref is not None, "Pool failed to initialize"

    async with pool_ref.acquire() as conn:
        await conn.execute("DROP TABLE IF EXISTS votes CASCADE")
        await conn.execute("DROP TABLE IF EXISTS matches CASCADE")
        await conn.execute("DROP TABLE IF EXISTS contestants CASCADE")
        await conn.execute("DROP TABLE IF EXISTS brackets CASCADE")

    # Reinitialize tables
    await db_module.init_db()

    yield pool_ref

    # Cleanup - close pool and restore original
    await pool_ref.close()

    db_module._pool = original_pool

    # Restore original DATABASE_URL
    if original_url:
        os.environ["DATABASE_URL"] = original_url
    elif "DATABASE_URL" in os.environ:
        del os.environ["DATABASE_URL"]


@pytest.fixture
async def bracket(test_db):
    """Create a test bracket."""
    bracket_id = await models.create_bracket(
        guild_id=123456789,
        channel_id=987654321,
        creator_id=111111111,
        title="Test Tournament",
    )
    return bracket_id


@pytest.fixture
async def bracket_with_contestants(bracket):
    """Create a bracket with test contestants."""
    names = ["Alice", "Bob", "Charlie", "David"]
    contestant_ids = []
    for name in names:
        cid = await models.add_contestant(bracket, name, 111111111)
        contestant_ids.append(cid)

    return bracket, contestant_ids
