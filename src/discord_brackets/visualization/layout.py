from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from discord_brackets import types, utils


@dataclass
class Box:
    name: str
    votes: int | None
    is_winner: bool


def flatten_bracket(tournament: types.Tournament) -> list[list[Box | None]]:
    if not tournament.rounds:
        raise ValueError("Tournament has no rounds")

    if tournament.rounds[0].name == "Play-in round":
        play_in_round, *rounds = tournament.rounds
    else:
        play_in_round, rounds = None, tournament.rounds
    tournament_size = len(rounds[0].matches) * 2

    result = []

    if play_in_round:
        result.append([None] * (tournament_size * 2))
        for match in play_in_round.matches:
            index = utils.get_recursive_seed_index(match.place, tournament_size * 2)
            result[-1][index] = Box(match.left.name, match.left.votes, match.left.winner)
            result[-1][index + 1] = Box(match.right.name, match.right.votes, match.right.winner)
    for round in rounds:
        result.append([None] * (len(round.matches) * 2))
        for match in round.matches:
            index = utils.get_recursive_seed_index(match.place, len(round.matches) * 2)
            result[-1][index] = Box(match.left.name, match.left.votes, match.left.winner)
            result[-1][index + 1] = Box(match.right.name, match.right.votes, match.right.winner)
    if len((last_round := rounds[-1]).matches) == 1:
        if (last_match := last_round.matches[0]).left.winner:
            result.append([Box(last_match.left.name, None, True)])
        elif last_match.right.winner:
            result.append([Box(last_match.right.name, None, True)])
    while len(result[-1]) > 1:
        result.append([Box("", None, False)] * (len(result[-1]) // 2))
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
