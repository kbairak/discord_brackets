from __future__ import annotations

import random
import math
from database import models


async def generate_bracket(bracket_id: int):
    """
    Generate the initial bracket structure with play-in rounds if needed.

    Simplified algorithm:
    1. Get all contestants and shuffle them
    2. Calculate if play-ins are needed (non-power-of-2 count)
    3. Create play-in matches if needed
    4. If no play-ins, create first round matches directly
    5. If play-ins exist, first round will be created when advancing from play-ins
    """
    contestants = await models.get_contestants(bracket_id)
    contestant_count = len(contestants)

    if contestant_count < 2:
        raise ValueError("Need at least 2 contestants to create a bracket")

    # Shuffle contestants for random seeding
    contestant_list = list(contestants)
    random.shuffle(contestant_list)

    # Find the next power of 2
    next_power = 2 ** math.ceil(math.log2(contestant_count))

    # Calculate how many play-in matches we need
    if contestant_count == next_power:
        # Perfect power of 2, no play-ins needed
        play_in_count = 0
    else:
        # We want to get down to next_power/2 contestants after play-ins
        target_after_play_ins = next_power // 2
        play_in_count = contestant_count - target_after_play_ins

    # Create play-in matches if needed
    if play_in_count > 0:
        for i in range(play_in_count):
            c1 = contestant_list[i * 2]
            c2 = contestant_list[i * 2 + 1]
            await models.create_match(
                bracket_id=bracket_id,
                round_number=0,  # Play-in round is round 0
                match_number=i,
                contestant_1_id=c1["id"],
                contestant_2_id=c2["id"],
                is_play_in=True,
            )

        # Update bracket to start at play-in round
        await models.update_bracket(bracket_id, current_round=0, phase="round_0")
    else:
        # No play-ins, create round 1 matches directly
        num_matches = contestant_count // 2

        for i in range(num_matches):
            c1 = contestant_list[i * 2]
            c2 = contestant_list[i * 2 + 1]
            await models.create_match(
                bracket_id=bracket_id,
                round_number=1,
                match_number=i,
                contestant_1_id=c1["id"],
                contestant_2_id=c2["id"],
                is_play_in=False,
            )

        # Update bracket to start at round 1
        await models.update_bracket(bracket_id, current_round=1, phase="round_1")


async def advance_round(bracket_id: int):
    """
    Advance to the next round by:
    1. Determining winners of current round matches
    2. Eliminating losers
    3. Creating next round matches

    Special handling for play-in rounds: combines play-in winners with direct entries.
    """
    bracket = await models.get_bracket(bracket_id)
    if bracket is None:
        raise ValueError(f"Bracket {bracket_id} not found")
    current_round = bracket["current_round"]

    # Get all matches from current round
    matches = await models.get_round_matches(bracket_id, current_round)

    # Determine winners and update matches
    winners = []
    for match in matches:
        match_id = match["id"]
        vote_counts = await models.get_vote_counts(match_id)

        c1_id = match["contestant_1_id"]
        c2_id = match["contestant_2_id"]

        # Handle byes (one contestant is None)
        if c1_id is None and c2_id is not None:
            winner_id = c2_id
        elif c2_id is None and c1_id is not None:
            winner_id = c1_id
        elif c1_id is None and c2_id is None:
            continue  # Empty match, skip
        else:
            # Both contestants present, count votes
            c1_votes = vote_counts.get(c1_id, 0)
            c2_votes = vote_counts.get(c2_id, 0)

            if c1_votes > c2_votes:
                winner_id = c1_id
                loser_id = c2_id
            elif c2_votes > c1_votes:
                winner_id = c2_id
                loser_id = c1_id
            else:
                # Tie - random tiebreaker
                winner_id = random.choice([c1_id, c2_id])
                loser_id = c2_id if winner_id == c1_id else c1_id

            # Eliminate loser
            await models.eliminate_contestant(loser_id, current_round)

        # Update match with winner
        await models.update_match(match_id, winner_id=winner_id)
        winners.append(winner_id)

    # Special handling for advancing from play-in round (round 0)
    # We need to include contestants who didn't participate in play-ins
    next_round = current_round + 1

    if current_round == 0:
        # Get play-in winners in match order to maintain bracket structure
        play_in_winners = []
        for match in matches:
            if match["winner_id"]:
                play_in_winners.append(match["winner_id"])

        # Get direct entries (contestants who didn't participate in play-ins)
        all_active = await models.get_contestants(bracket_id, include_eliminated=False)
        direct_entries = [c["id"] for c in all_active if c["id"] not in play_in_winners]

        # Interleave play-in winners with direct entries to maintain visual flow
        # This keeps the bracket structure clean and prevents line crossings
        active_ids = []
        play_in_idx = 0
        direct_idx = 0

        # Alternate: direct entry, play-in winner, direct entry, play-in winner...
        # This ensures play-in winners stay near their original positions
        while play_in_idx < len(play_in_winners) or direct_idx < len(direct_entries):
            if direct_idx < len(direct_entries):
                active_ids.append(direct_entries[direct_idx])
                direct_idx += 1
            if play_in_idx < len(play_in_winners):
                active_ids.append(play_in_winners[play_in_idx])
                play_in_idx += 1

        # Create round 1 matches with all active contestants
        matches_needed = len(active_ids) // 2

        for i in range(matches_needed):
            c1_id = active_ids[i * 2] if i * 2 < len(active_ids) else None
            c2_id = active_ids[i * 2 + 1] if i * 2 + 1 < len(active_ids) else None

            await models.create_match(
                bracket_id=bracket_id,
                round_number=next_round,
                match_number=i,
                contestant_1_id=c1_id,
                contestant_2_id=c2_id,
                is_play_in=False,
            )
    else:
        # Normal round advancement - pair up winners

        # Check if this was the final match
        if len(winners) == 1:
            await models.update_bracket(bracket_id, phase="completed")
            return

        matches_needed = len(winners) // 2

        for i in range(matches_needed):
            c1_id = winners[i * 2] if i * 2 < len(winners) else None
            c2_id = winners[i * 2 + 1] if i * 2 + 1 < len(winners) else None

            await models.create_match(
                bracket_id=bracket_id,
                round_number=next_round,
                match_number=i,
                contestant_1_id=c1_id,
                contestant_2_id=c2_id,
                is_play_in=False,
            )

    # Update bracket
    await models.update_bracket(
        bracket_id, current_round=next_round, phase=f"round_{next_round}"
    )


async def get_winner(bracket_id: int):
    """Get the winner of a completed bracket."""
    bracket = await models.get_bracket(bracket_id)
    if bracket is None or bracket["phase"] != "completed":
        return None

    # The winner is the contestant who was never eliminated
    contestants = await models.get_contestants(bracket_id, include_eliminated=True)
    for contestant in contestants:
        if contestant["eliminated_in_round"] is None:
            return contestant

    return None
