import pytest
from database import models
from bracket import logic


@pytest.mark.asyncio
async def test_generate_bracket_power_of_2(bracket):
    """Test bracket generation with power of 2 contestants (4)."""
    # Add 4 contestants
    for i in range(4):
        await models.add_contestant(bracket, f"Player {i + 1}", 111)

    await logic.generate_bracket(bracket)

    # Check bracket state
    bracket_data = await models.get_bracket(bracket)
    assert bracket_data is not None
    assert bracket_data["current_round"] == 1  # Should start at round 1 (no play-ins)
    assert bracket_data["phase"] == "round_1"

    # Should have 2 matches in round 1
    round_1_matches = await models.get_round_matches(bracket, 1)
    assert len(round_1_matches) == 2

    # No play-in matches
    play_in_matches = await models.get_round_matches(bracket, 0)
    assert len(play_in_matches) == 0

    # All matches should have both contestants
    for match in round_1_matches:
        assert match["contestant_1_id"] is not None
        assert match["contestant_2_id"] is not None


@pytest.mark.asyncio
async def test_generate_bracket_two_contestants(bracket):
    """Test bracket generation with minimum contestants (2)."""
    await models.add_contestant(bracket, "Player 1", 111)
    await models.add_contestant(bracket, "Player 2", 111)

    await logic.generate_bracket(bracket)

    bracket_data = await models.get_bracket(bracket)
    assert bracket_data is not None
    assert bracket_data["current_round"] == 1

    # Should have exactly 1 match
    round_1_matches = await models.get_round_matches(bracket, 1)
    assert len(round_1_matches) == 1

    match = round_1_matches[0]
    assert match["contestant_1_id"] is not None
    assert match["contestant_2_id"] is not None


@pytest.mark.asyncio
async def test_generate_bracket_with_play_ins(bracket):
    """Test bracket generation with 5 contestants (requires play-ins)."""
    # Add 5 contestants
    for i in range(5):
        await models.add_contestant(bracket, f"Player {i + 1}", 111)

    await logic.generate_bracket(bracket)

    bracket_data = await models.get_bracket(bracket)
    assert bracket_data is not None
    assert bracket_data["current_round"] == 0  # Should start at play-in round

    # Should have 1 play-in match (5 -> 4, next power of 2)
    play_in_matches = await models.get_round_matches(bracket, 0)
    assert len(play_in_matches) == 1
    assert (
        play_in_matches[0]["is_play_in"] is True
        or play_in_matches[0]["is_play_in"] == 1
    )

    # Round 1 should NOT be created yet (will be created when advancing from play-ins)
    round_1_matches = await models.get_round_matches(bracket, 1)
    assert len(round_1_matches) == 0


@pytest.mark.asyncio
async def test_generate_bracket_13_contestants(bracket):
    """Test bracket generation with 13 contestants (complex play-in scenario)."""
    # Add 13 contestants
    for i in range(13):
        await models.add_contestant(bracket, f"Player {i + 1}", 111)

    await logic.generate_bracket(bracket)

    bracket_data = await models.get_bracket(bracket)
    assert bracket_data is not None
    assert bracket_data["current_round"] == 0  # Play-in round

    # 13 contestants -> next power of 2 is 16 -> need to get to 8 after play-ins
    # So we need 13 - 8 = 5 play-in matches
    play_in_matches = await models.get_round_matches(bracket, 0)
    assert len(play_in_matches) == 5


@pytest.mark.asyncio
async def test_generate_bracket_too_few_contestants(bracket):
    """Test that bracket generation fails with only 1 contestant."""
    await models.add_contestant(bracket, "Lonely Player", 111)

    with pytest.raises(ValueError, match="at least 2 contestants"):
        await logic.generate_bracket(bracket)


@pytest.mark.asyncio
async def test_advance_round_simple(bracket):
    """Test advancing from one round to the next."""
    # Set up a simple bracket with 4 contestants
    contestant_ids = []
    for i in range(4):
        cid = await models.add_contestant(bracket, f"Player {i + 1}", 111)
        contestant_ids.append(cid)

    await logic.generate_bracket(bracket)

    # Get round 1 matches
    round_1_matches = await models.get_round_matches(bracket, 1)
    assert len(round_1_matches) == 2

    # Simulate voting on both matches
    for match in round_1_matches:
        match_id = match["id"]
        # Vote for contestant 1 in each match
        await models.add_vote(
            match_id, user_id=1, contestant_id=match["contestant_1_id"]
        )
        await models.add_vote(
            match_id, user_id=2, contestant_id=match["contestant_1_id"]
        )
        await models.add_vote(
            match_id, user_id=3, contestant_id=match["contestant_2_id"]
        )

    # Advance to round 2
    await logic.advance_round(bracket)

    # Check bracket state
    bracket_data = await models.get_bracket(bracket)
    assert bracket_data is not None
    assert bracket_data["current_round"] == 2
    assert bracket_data["phase"] == "round_2"

    # Should have 1 match in round 2 (finals)
    round_2_matches = await models.get_round_matches(bracket, 2)
    assert len(round_2_matches) == 1

    # Both contestants in finals should be winners from round 1
    final_match = round_2_matches[0]
    assert final_match["contestant_1_id"] == round_1_matches[0]["contestant_1_id"]
    assert final_match["contestant_2_id"] == round_1_matches[1]["contestant_1_id"]


@pytest.mark.asyncio
async def test_advance_to_completion(bracket):
    """Test completing a full bracket."""
    # Create simple 2-person bracket
    c1_id = await models.add_contestant(bracket, "Winner", 111)
    await models.add_contestant(bracket, "Loser", 111)

    await logic.generate_bracket(bracket)

    # Get the only match
    matches = await models.get_round_matches(bracket, 1)
    assert len(matches) == 1

    # Vote for winner
    await models.add_vote(matches[0]["id"], user_id=1, contestant_id=c1_id)
    await models.add_vote(matches[0]["id"], user_id=2, contestant_id=c1_id)

    # Advance (should complete)
    await logic.advance_round(bracket)

    # Check bracket is completed
    bracket_data = await models.get_bracket(bracket)
    assert bracket_data is not None
    assert bracket_data["phase"] == "completed"


@pytest.mark.asyncio
async def test_get_winner(bracket):
    """Test getting the winner of a completed bracket."""
    c1_id = await models.add_contestant(bracket, "Champion", 111)
    await models.add_contestant(bracket, "Runner-up", 111)

    await logic.generate_bracket(bracket)

    matches = await models.get_round_matches(bracket, 1)

    # Champion wins
    await models.add_vote(matches[0]["id"], user_id=1, contestant_id=c1_id)

    await logic.advance_round(bracket)

    # Get winner
    winner = await logic.get_winner(bracket)
    assert winner is not None
    assert winner["name"] == "Champion"
    assert winner["id"] == c1_id


@pytest.mark.asyncio
async def test_tie_breaking(bracket):
    """Test that ties are broken (randomly)."""
    c1_id = await models.add_contestant(bracket, "Player 1", 111)
    c2_id = await models.add_contestant(bracket, "Player 2", 111)

    await logic.generate_bracket(bracket)

    matches = await models.get_round_matches(bracket, 1)
    match_id = matches[0]["id"]

    # Create a tie - no votes at all
    # (or equal votes would work too)

    # Advance should still work and pick a winner
    await logic.advance_round(bracket)

    # Check that a winner was selected
    match = await models.get_match(match_id)
    assert match is not None
    assert match["winner_id"] is not None
    assert match["winner_id"] in [c1_id, c2_id]


@pytest.mark.asyncio
async def test_bye_handling(bracket):
    """Test that byes are handled correctly."""
    # Create 3 contestants - should create 1 match + 1 bye
    for i in range(3):
        await models.add_contestant(bracket, f"Player {i + 1}", 111)

    await logic.generate_bracket(bracket)

    # Should start with play-in round
    bracket_data = await models.get_bracket(bracket)
    assert bracket_data is not None
    assert bracket_data["current_round"] == 0

    # Should have 1 play-in match (3 -> 2)
    play_in_matches = await models.get_round_matches(bracket, 0)
    assert len(play_in_matches) == 1

    # Vote and advance
    play_in = play_in_matches[0]
    await models.add_vote(
        play_in["id"], user_id=1, contestant_id=play_in["contestant_1_id"]
    )
    await logic.advance_round(bracket)

    # Now in round 1
    bracket_data = await models.get_bracket(bracket)
    assert bracket_data is not None
    assert bracket_data["current_round"] == 1
