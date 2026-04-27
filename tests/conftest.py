"""Test configuration and fixtures for discord_brackets tests."""

import asyncio
import os
import random

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

# Set DATABASE_URL before importing db module
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from discord_brackets import db, models  # noqa: E402


# Initialize database schema once at module load
asyncio.run(db.init_db())


@pytest.fixture(autouse=True)
async def clean_db():
    """Truncate all tables after each test for isolation."""
    yield
    # Clean up after test
    async with AsyncSession(db.get_engine()) as session, session.begin():
        await session.execute(delete(models.Vote))
        await session.execute(delete(models.Match))
        await session.execute(delete(models.Pin))
        await session.execute(delete(models.Option))
        await session.execute(delete(models.Tournament))


@pytest.fixture(autouse=True)
def seeded_random():
    """Seed random number generator for deterministic tests."""
    random.seed(42)
    yield
    # Reset to default random state
    random.seed()
