from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from discord_brackets import types


@dataclass
class Box:
    """Represents a single option box in the bracket layout.

    Attributes:
        name: The option name (empty string for unfinished matches)
        votes: Vote count (None for champion or unfinished matches)
        is_winner: Whether this option won their match
    """

    name: str
    votes: int | None
    is_winner: bool


def flatten_bracket(tournament: types.Tournament) -> list[list[Box | None]]:
    """Convert a tournament into a flat bracket representation.

    Takes a tournament and returns a nested list structure where:
    - All rounds are represented, even if they don't exist yet
    - Each list contains all participants (both left and right from each match)
    - Play-in rounds use None for bye positions (higher seeds)
    - Unfinished matches use Box('', None, False)
    - Final list contains the champion (or Box('', None, False) if not finished)

    Args:
        tournament: A Tournament (supports both power-of-two and play-in)

    Returns:
        Nested list of Box | None objects representing the bracket progression

    Raises:
        ValueError: If tournament is empty

    Example:
        For a completed 8-option tournament:
        [
            [Box('one', 1, False), Box('two', 2, True), ...],  # 8 boxes
            [Box('two', 4, False), Box('four', 8, True), ...],  # 4 boxes
            [Box('four', 16, False), Box('eight', 32, True)],   # 2 boxes
            [Box('eight', None, True)],                          # 1 box (champion)
        ]

        For a 10-option tournament with play-in (8+2):
        [
            [None, None, None, None, Box('opt6'), Box('opt9'), Box('opt7'), Box('opt8')],  # Play-in
            [Box('one', 1, False), Box('two', 2, True), ...],  # Round 1: 8 boxes
            [Box('two', 4, False), Box('four', 8, True), ...],  # Round 2: 4 boxes
            [Box('four', 16, False), Box('eight', 32, True)],   # Round 3: 2 boxes
            [Box('eight', None, True)],                          # Champion
        ]
    """
    if not tournament.rounds:
        raise ValueError("Tournament has no rounds")

    # Determine tournament size and detect play-in round
    first_round = tournament.rounds[0]
    has_play_in = first_round.name == "Play-in round"

    if has_play_in:
        # Play-in round exists - tournament size is determined by the NEXT round
        if len(tournament.rounds) > 1:
            # Use Round 1 to determine tournament size
            tournament_size = len(tournament.rounds[1].matches) * 2
        else:
            # Only play-in exists, calculate from play-in
            # play_in_size = (total_options - tournament_size) * 2
            # Reverse: tournament_size = total - (play_in_matches * 2 / 2)
            # Actually, need to find the power of 2 that makes sense
            play_in_matches = len(first_round.matches)
            play_in_participants = play_in_matches * 2
            # Total participants = tournament_size + (play_in_participants / 2 * something)
            # For 10 options: tournament_size=8, play_in=2 matches=4 participants
            # Formula: tournament_size is the next power of 2 >= play_in_participants
            tournament_size = 1 << (play_in_participants.bit_length())
    else:
        # No play-in - first round determines size
        tournament_size = len(first_round.matches) * 2

    # Calculate total regular rounds (log2 of tournament size)
    total_rounds = int(math.log2(tournament_size))

    result: list[list[Box | None]] = []

    # Handle play-in round if it exists
    if has_play_in:
        play_in_round = tournament.rounds[0]

        # The play-in round needs to be structured so that when widen_bracket splits it,
        # each play-in match ends up on the correct side to feed its Round 1 match
        # We create tournament_size * 2 slots and place matches based on Round 1 connections

        total_play_in_slots = tournament_size * 2
        boxes: list[Box | None] = [None] * total_play_in_slots

        # If Round 1 exists, place play-in matches based on their Round 1 connections
        if len(tournament.rounds) > 1:
            round_1 = tournament.rounds[1]
            mid_point = total_play_in_slots // 2
            placed_matches: set[int] = set()

            # Try to map each play-in match to the specific R1 box it feeds
            # This uses the match ID stored in advanced_from
            for play_in_idx, play_in_match in enumerate(play_in_round.matches):
                # Find which specific R1 box this play-in feeds into
                r1_box_idx = None
                for r1_match_idx, r1_match in enumerate(round_1.matches):
                    if r1_match.left.advanced_from == play_in_match.id:
                        r1_box_idx = r1_match_idx * 2  # Left side of match
                        break
                    elif r1_match.right.advanced_from == play_in_match.id:
                        r1_box_idx = r1_match_idx * 2 + 1  # Right side of match
                        break

                if r1_box_idx is not None:
                    # R1 boxes are split: 0,1 go to left half, 2,3 go to right half
                    # Place play-in in the corresponding position
                    if r1_box_idx < len(round_1.matches):
                        # Left half of R1 (boxes 0, 1)
                        # Map R1 box 0 → play-in 0-1, R1 box 1 → play-in 2-3
                        play_in_pos = r1_box_idx * 2
                    else:
                        # Right half of R1 (boxes 2, 3)
                        # Map R1 box 2 → play-in 4-5, R1 box 3 → play-in 6-7
                        play_in_pos = mid_point + (r1_box_idx - len(round_1.matches)) * 2

                    boxes[play_in_pos] = Box(play_in_match.left.name, play_in_match.left.votes, play_in_match.left.winner)
                    boxes[play_in_pos + 1] = Box(play_in_match.right.name, play_in_match.right.votes, play_in_match.right.winner)
                    placed_matches.add(play_in_idx)

            # Fallback: if any matches weren't placed (advanced_from is None or doesn't match),
            # place them at the end in order
            if len(placed_matches) < len(play_in_round.matches):
                actual_matches = len(play_in_round.matches)
                actual_boxes = actual_matches * 2
                bye_count = total_play_in_slots - actual_boxes
                for i, match in enumerate(play_in_round.matches):
                    if i not in placed_matches:
                        boxes[bye_count + i * 2] = Box(match.left.name, match.left.votes, match.left.winner)
                        boxes[bye_count + i * 2 + 1] = Box(match.right.name, match.right.votes, match.right.winner)
        else:
            # No Round 1 yet, just place matches in order at the end
            actual_matches = len(play_in_round.matches)
            actual_boxes = actual_matches * 2
            bye_count = total_play_in_slots - actual_boxes
            for i, match in enumerate(play_in_round.matches):
                boxes[bye_count + i * 2] = Box(match.left.name, match.left.votes, match.left.winner)
                boxes[bye_count + i * 2 + 1] = Box(match.right.name, match.right.votes, match.right.winner)

        result.append(boxes)

    # Process regular rounds
    for round_idx in range(total_rounds):
        boxes_list: list[Box | None] = []
        expected_matches = tournament_size // (2 ** (round_idx + 1))

        # Adjust tournament round index based on play-in
        tournament_round_idx = round_idx + (1 if has_play_in else 0)

        if tournament_round_idx < len(tournament.rounds):
            # Round exists - process actual matches
            round = tournament.rounds[tournament_round_idx]
            matches = list(round.matches)

            # For rounds that follow play-ins (Round 1), reorder matches based on advanced_from
            # to ensure correct bracket structure visualization
            if has_play_in and round_idx == 0:
                # Sort matches by the play-in match they came from (advanced_from)
                # Matches should be ordered by which play-in match their participant came from
                def get_play_in_source(match: types.Match) -> tuple[int, int]:
                    """Get the play-in match indices for this match's participants."""
                    left_from = match.left.advanced_from if match.left.advanced_from is not None else -1
                    right_from = match.right.advanced_from if match.right.advanced_from is not None else -1
                    # Return max so matches with advanced players are ordered by their source
                    return (max(left_from, right_from), min(left_from, right_from))

                matches = sorted(matches, key=get_play_in_source, reverse=True)

            for match in matches:
                boxes_list.append(Box(match.left.name, match.left.votes, match.left.winner))
                boxes_list.append(Box(match.right.name, match.right.votes, match.right.winner))
        else:
            # Round doesn't exist yet - generate empty boxes
            for _ in range(expected_matches):
                boxes_list.append(Box("", None, False))
                boxes_list.append(Box("", None, False))

        result.append(boxes_list)

    # Add final list with champion
    # Check if tournament is finished (last round has a winner)
    last_regular_round_idx = total_rounds - 1 + (1 if has_play_in else 0)

    if last_regular_round_idx < len(tournament.rounds):
        last_round = tournament.rounds[last_regular_round_idx]
        last_match = last_round.matches[0]

        if last_match.left.winner:
            result.append([Box(last_match.left.name, None, True)])
        elif last_match.right.winner:
            result.append([Box(last_match.right.name, None, True)])
        else:
            result.append([Box("", None, False)])
    else:
        # Tournament not finished yet
        result.append([Box("", None, False)])

    return result


def widen_bracket(flat: Sequence[Sequence[Box | None]]) -> list[list[Box | None]]:
    """Transform flat bracket layout to wide format.

    Splits each round (except champion) into left and right halves,
    creating a traditional bracket visualization structure.

    Args:
        flat: Flat bracket layout from flatten_bracket()

    Returns:
        Wide bracket layout with columns split

    Example:
        Flat: [[A, B, C, D], [E, F], [G]]
        Wide: [[A, B], [E], [G], [F], [C, D]]
              (left halves, champion, right halves reversed)
    """
    if not flat:
        return []

    # All rounds except the champion
    rounds = flat[:-1]
    champion = flat[-1]

    result: list[list[Box | None]] = []

    # Add left halves (first half of each round)
    for round_boxes in rounds:
        mid = len(round_boxes) // 2
        result.append(list(round_boxes[:mid]))

    # Add champion in the middle
    result.append(list(champion))

    # Add right halves (second half of each round, in reverse order)
    for round_boxes in reversed(rounds):
        mid = len(round_boxes) // 2
        result.append(list(round_boxes[mid:]))

    return result
