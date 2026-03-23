import pytest
from database import models
from bracket import logic, get_winner


@pytest.mark.asyncio
async def test_full_tournament_flow_4_contestants(bracket):
    """Test complete tournament with 4 contestants (no play-ins)."""
    # Phase 1: Collection
    contestant_ids = []
    names = ["Alice", "Bob", "Charlie", "David"]
    for name in names:
        cid = await models.add_contestant(bracket, name, 111)
        contestant_ids.append(cid)

    # Verify collection phase
    bracket_data = await models.get_bracket(bracket)
    assert bracket_data is not None
    assert bracket_data["phase"] == "collection"

    # Phase 2: Preview (simulated by updating phase)
    await models.update_bracket(bracket, phase="preview")

    # Phase 3: Generate bracket
    await logic.generate_bracket(bracket)

    bracket_data = await models.get_bracket(bracket)
    assert bracket_data is not None
    assert bracket_data["phase"] == "round_1"
    assert bracket_data["current_round"] == 1

    # Round 1: 2 matches
    round_1_matches = await models.get_round_matches(bracket, 1)
    assert len(round_1_matches) == 2

    # Simulate voting on Round 1
    # Match 1: contestant 0 wins
    await models.add_vote(
        round_1_matches[0]["id"], 1, round_1_matches[0]["contestant_1_id"]
    )
    await models.add_vote(
        round_1_matches[0]["id"], 2, round_1_matches[0]["contestant_1_id"]
    )
    await models.add_vote(
        round_1_matches[0]["id"], 3, round_1_matches[0]["contestant_2_id"]
    )

    # Match 2: contestant 1 wins
    await models.add_vote(
        round_1_matches[1]["id"], 4, round_1_matches[1]["contestant_1_id"]
    )
    await models.add_vote(
        round_1_matches[1]["id"], 5, round_1_matches[1]["contestant_1_id"]
    )

    # Advance to Round 2 (Finals)
    await logic.advance_round(bracket)

    bracket_data = await models.get_bracket(bracket)
    assert bracket_data is not None
    assert bracket_data["phase"] == "round_2"
    assert bracket_data["current_round"] == 2

    # Round 2: 1 match (finals)
    round_2_matches = await models.get_round_matches(bracket, 2)
    assert len(round_2_matches) == 1

    # Get the finals match
    finals = round_2_matches[0]

    # Simulate voting on finals
    await models.add_vote(finals["id"], 10, finals["contestant_1_id"])
    await models.add_vote(finals["id"], 11, finals["contestant_1_id"])
    await models.add_vote(finals["id"], 12, finals["contestant_1_id"])

    # Complete the tournament
    await logic.advance_round(bracket)

    bracket_data = await models.get_bracket(bracket)
    assert bracket_data is not None
    assert bracket_data["phase"] == "completed"

    # Verify winner
    winner = await get_winner(bracket)
    assert winner is not None
    assert winner["id"] == finals["contestant_1_id"]


@pytest.mark.asyncio
async def test_full_tournament_flow_with_play_ins(bracket):
    """Test complete tournament with 6 contestants (requires play-ins)."""
    # Add 6 contestants
    for i in range(6):
        await models.add_contestant(bracket, f"Player {i + 1}", 111)

    # Generate bracket
    await logic.generate_bracket(bracket)

    bracket_data = await models.get_bracket(bracket)
    assert bracket_data is not None
    assert bracket_data["current_round"] == 0  # Play-in round
    assert bracket_data["phase"] == "round_0"

    # Play-in round: should have 2 play-in matches (6 -> 4)
    play_in_matches = await models.get_round_matches(bracket, 0)
    assert len(play_in_matches) == 2

    # Vote on play-ins
    for match in play_in_matches:
        # First contestant wins each play-in
        await models.add_vote(match["id"], 1, match["contestant_1_id"])
        await models.add_vote(match["id"], 2, match["contestant_1_id"])

    # Advance past play-ins
    await logic.advance_round(bracket)

    bracket_data = await models.get_bracket(bracket)
    assert bracket_data is not None
    assert bracket_data["current_round"] == 1
    assert bracket_data["phase"] == "round_1"

    # Round 1 should now have matches
    round_1_matches = await models.get_round_matches(bracket, 1)
    assert len(round_1_matches) == 2

    # Vote on round 1
    for match in round_1_matches:
        if match["contestant_1_id"] and match["contestant_2_id"]:
            await models.add_vote(match["id"], 10, match["contestant_1_id"])

    # Advance to finals
    await logic.advance_round(bracket)

    bracket_data = await models.get_bracket(bracket)
    assert bracket_data is not None
    assert bracket_data["current_round"] == 2

    # Finals
    finals = await models.get_round_matches(bracket, 2)
    assert len(finals) == 1

    # Vote on finals
    await models.add_vote(finals[0]["id"], 20, finals[0]["contestant_1_id"])

    # Complete
    await logic.advance_round(bracket)

    bracket_data = await models.get_bracket(bracket)
    assert bracket_data is not None
    assert bracket_data["phase"] == "completed"

    winner = await get_winner(bracket)
    assert winner is not None


@pytest.mark.asyncio
async def test_tournament_with_13_contestants(bracket):
    """Test tournament with 13 contestants (complex play-in scenario)."""
    # Add 13 contestants
    for i in range(13):
        await models.add_contestant(bracket, f"Contestant {i + 1}", 111)

    # Generate bracket
    await logic.generate_bracket(bracket)

    bracket_data = await models.get_bracket(bracket)
    assert bracket_data is not None
    assert bracket_data["current_round"] == 0

    # Should have 5 play-in matches
    play_in_matches = await models.get_round_matches(bracket, 0)
    assert len(play_in_matches) == 5

    # Simulate voting through all rounds until completion
    current_round = 0
    max_rounds = 10  # Safety limit

    while current_round < max_rounds:
        bracket_data = await models.get_bracket(bracket)
        assert bracket_data is not None

        if bracket_data["phase"] == "completed":
            break

        # Get current round matches
        matches = await models.get_round_matches(bracket, bracket_data["current_round"])

        # Vote on all matches
        for match in matches:
            if match["contestant_1_id"] and match["contestant_2_id"]:
                # First contestant wins
                await models.add_vote(
                    match["id"], current_round * 100 + 1, match["contestant_1_id"]
                )
            elif match["contestant_1_id"]:
                # Bye - contestant 1 advances automatically
                await models.update_match(
                    match["id"], winner_id=match["contestant_1_id"]
                )
            elif match["contestant_2_id"]:
                # Bye - contestant 2 advances automatically
                await models.update_match(
                    match["id"], winner_id=match["contestant_2_id"]
                )

        # Advance round
        await logic.advance_round(bracket)
        current_round += 1

    # Verify completion
    bracket_data = await models.get_bracket(bracket)
    assert bracket_data is not None
    assert bracket_data["phase"] == "completed"

    winner = await get_winner(bracket)
    assert winner is not None


@pytest.mark.asyncio
async def test_multiple_users_voting(bracket):
    """Test that multiple users can vote independently."""
    # Create simple 2-person bracket
    c1_id = await models.add_contestant(bracket, "Popular", 111)
    c2_id = await models.add_contestant(bracket, "Unpopular", 111)

    await logic.generate_bracket(bracket)

    matches = await models.get_round_matches(bracket, 1)
    match_id = matches[0]["id"]

    # Multiple users vote for c1
    for user_id in range(1, 6):
        success = await models.add_vote(match_id, user_id, c1_id)
        assert success is True

    # One user votes for c2
    success = await models.add_vote(match_id, 99, c2_id)
    assert success is True

    # Get vote counts
    vote_counts = await models.get_vote_counts(match_id)
    assert vote_counts[c1_id] == 5
    assert vote_counts[c2_id] == 1

    # Advance - c1 should win
    await logic.advance_round(bracket)

    winner = await get_winner(bracket)
    assert winner is not None
    assert winner["id"] == c1_id


@pytest.mark.asyncio
async def test_contestant_elimination_tracking(bracket):
    """Test that eliminated contestants are tracked correctly."""
    # Create 4-person bracket
    for i in range(4):
        await models.add_contestant(bracket, f"Player {i + 1}", 111)

    await logic.generate_bracket(bracket)

    # Round 1
    round_1_matches = await models.get_round_matches(bracket, 1)

    for match in round_1_matches:
        # Contestant 1 wins each match
        await models.add_vote(match["id"], 1, match["contestant_1_id"])

    await logic.advance_round(bracket)

    # Check that 2 contestants were eliminated in round 1
    all_contestants = await models.get_contestants(bracket, include_eliminated=True)
    eliminated = [c for c in all_contestants if c["eliminated_in_round"] == 1]
    assert len(eliminated) == 2

    # Round 2 (finals)
    round_2_matches = await models.get_round_matches(bracket, 2)
    await models.add_vote(
        round_2_matches[0]["id"], 2, round_2_matches[0]["contestant_1_id"]
    )

    await logic.advance_round(bracket)

    # Check that 1 more contestant was eliminated in round 2
    all_contestants = await models.get_contestants(bracket, include_eliminated=True)
    eliminated_r2 = [c for c in all_contestants if c["eliminated_in_round"] == 2]
    assert len(eliminated_r2) == 1

    # Winner should not be eliminated
    winner = await get_winner(bracket)
    assert winner is not None
    assert winner["eliminated_in_round"] is None
