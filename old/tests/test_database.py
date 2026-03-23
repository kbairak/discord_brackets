import pytest
from database import models


@pytest.mark.asyncio
async def test_create_bracket(test_db):
    """Test creating a bracket."""
    bracket_id = await models.create_bracket(
        guild_id=123, channel_id=456, creator_id=789, title="Test Bracket"
    )

    assert bracket_id > 0

    bracket = await models.get_bracket(bracket_id)
    assert bracket is not None
    assert bracket["title"] == "Test Bracket"
    assert bracket["phase"] == "collection"
    assert bracket["current_round"] == 0


@pytest.mark.asyncio
async def test_add_contestant(bracket):
    """Test adding contestants."""
    contestant_id = await models.add_contestant(bracket, "Test Player", 999)

    assert contestant_id > 0

    contestant = await models.get_contestant(contestant_id)
    assert contestant is not None
    assert contestant["name"] == "Test Player"
    assert contestant["bracket_id"] == bracket


@pytest.mark.asyncio
async def test_get_contestants(bracket_with_contestants):
    """Test retrieving contestants."""
    bracket_id, contestant_ids = bracket_with_contestants

    contestants = await models.get_contestants(bracket_id)
    assert len(contestants) == 4

    names = [c["name"] for c in contestants]
    assert "Alice" in names
    assert "Bob" in names
    assert "Charlie" in names
    assert "David" in names


@pytest.mark.asyncio
async def test_update_contestants(bracket):
    """Test updating contestants list."""
    # Add initial contestants
    await models.add_contestant(bracket, "Old 1", 111)
    await models.add_contestant(bracket, "Old 2", 111)

    # Update with new list
    new_names = ["New 1", "New 2", "New 3"]
    await models.update_contestants(bracket, new_names, 222)

    contestants = await models.get_contestants(bracket)
    assert len(contestants) == 3

    names = [c["name"] for c in contestants]
    assert names == ["New 1", "New 2", "New 3"]


@pytest.mark.asyncio
async def test_create_match(bracket_with_contestants):
    """Test creating a match."""
    bracket_id, contestant_ids = bracket_with_contestants

    match_id = await models.create_match(
        bracket_id=bracket_id,
        round_number=1,
        match_number=0,
        contestant_1_id=contestant_ids[0],
        contestant_2_id=contestant_ids[1],
        is_play_in=False,
    )

    assert match_id > 0

    match = await models.get_match(match_id)
    assert match is not None
    assert match["round_number"] == 1
    assert match["contestant_1_id"] == contestant_ids[0]
    assert match["contestant_2_id"] == contestant_ids[1]


@pytest.mark.asyncio
async def test_add_vote(bracket_with_contestants):
    """Test adding votes."""
    bracket_id, contestant_ids = bracket_with_contestants

    # Create a match
    match_id = await models.create_match(
        bracket_id=bracket_id,
        round_number=1,
        match_number=0,
        contestant_1_id=contestant_ids[0],
        contestant_2_id=contestant_ids[1],
    )

    # Add first vote
    success = await models.add_vote(
        match_id, user_id=1, contestant_id=contestant_ids[0]
    )
    assert success is True

    # Try duplicate vote (should fail)
    success = await models.add_vote(
        match_id, user_id=1, contestant_id=contestant_ids[1]
    )
    assert success is False

    # Different user can vote
    success = await models.add_vote(
        match_id, user_id=2, contestant_id=contestant_ids[1]
    )
    assert success is True


@pytest.mark.asyncio
async def test_vote_counts(bracket_with_contestants):
    """Test vote counting."""
    bracket_id, contestant_ids = bracket_with_contestants

    match_id = await models.create_match(
        bracket_id=bracket_id,
        round_number=1,
        match_number=0,
        contestant_1_id=contestant_ids[0],
        contestant_2_id=contestant_ids[1],
    )

    # Add votes
    await models.add_vote(match_id, user_id=1, contestant_id=contestant_ids[0])
    await models.add_vote(match_id, user_id=2, contestant_id=contestant_ids[0])
    await models.add_vote(match_id, user_id=3, contestant_id=contestant_ids[1])

    vote_counts = await models.get_vote_counts(match_id)

    assert vote_counts[contestant_ids[0]] == 2
    assert vote_counts[contestant_ids[1]] == 1


@pytest.mark.asyncio
async def test_eliminate_contestant(bracket_with_contestants):
    """Test eliminating a contestant."""
    bracket_id, contestant_ids = bracket_with_contestants

    # Eliminate first contestant
    await models.eliminate_contestant(contestant_ids[0], round_number=1)

    # Check they're eliminated
    contestant = await models.get_contestant(contestant_ids[0])
    assert contestant is not None
    assert contestant["eliminated_in_round"] == 1

    # Get non-eliminated contestants
    active = await models.get_contestants(bracket_id, include_eliminated=False)
    assert len(active) == 3

    # Get all contestants including eliminated
    all_contestants = await models.get_contestants(bracket_id, include_eliminated=True)
    assert len(all_contestants) == 4
