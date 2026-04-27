from __future__ import annotations

import pytest

from discord_brackets import types
from discord_brackets.visualization.layout import Box, flatten_bracket, widen_bracket


def test_4_option_tournament():
    """Test 4-option tournament with bracket seeding.

    Bracket order for 4 options: [0, 3, 1, 2]
    - Match with place=0 goes to position 0 (seed 1 vs 4)
    - Match with place=1 goes to position 2 (seed 2 vs 3)
    After reordering: [(1,4), (2,3)]
    """
    tournament = types.Tournament(
        2,
        [
            types.Round(
                "Round 1",
                [
                    types.Match(
                        1,
                        types.Option("one", 10, True, None),
                        types.Option("four", 5, False, None),
                        0,
                    ),
                    types.Match(
                        2,
                        types.Option("two", 7, False, None),
                        types.Option("three", 12, True, None),
                        1,
                    ),
                ],
            ),
            types.Round(
                "Final",
                [
                    types.Match(
                        3,
                        types.Option("one", 20, False, None),
                        types.Option("three", 25, True, None),
                        0,
                    )
                ],
            ),
        ],
    )

    result = flatten_bracket(tournament)

    # Round 1: bracket order [0, 3, 1, 2] with 4 slots
    # place=0 → index 0 → (one, four)
    # place=1 → index 2 → (two, three)
    assert result == [
        [
            Box("one", 10, True),
            Box("four", 5, False),
            Box("two", 7, False),
            Box("three", 12, True),
        ],
        [Box("one", 20, False), Box("three", 25, True)],
        [Box("three", None, True)],
    ]


def test_8_option_tournament():
    """Test 8-option tournament with bracket seeding.

    Bracket order for 8 options: [0, 7, 3, 4, 1, 6, 2, 5]
    Matches in bracket order:
    - place=0: (1,8) at index 0
    - place=3: (4,5) at index 2
    - place=1: (2,7) at index 4
    - place=2: (3,6) at index 6
    """
    tournament = types.Tournament(
        1,
        [
            types.Round(
                "Round 1",
                [
                    types.Match(
                        1,
                        types.Option("one", 1, True, None),
                        types.Option("eight", 2, False, None),
                        0,
                    ),
                    types.Match(
                        2,
                        types.Option("four", 3, True, None),
                        types.Option("five", 4, False, None),
                        3,
                    ),
                    types.Match(
                        3,
                        types.Option("two", 5, True, None),
                        types.Option("seven", 6, False, None),
                        1,
                    ),
                    types.Match(
                        4,
                        types.Option("three", 7, True, None),
                        types.Option("six", 8, False, None),
                        2,
                    ),
                ],
            ),
            types.Round(
                "Round 2",
                [
                    types.Match(
                        5,
                        types.Option("one", 4, True, None),
                        types.Option("four", 8, False, None),
                        0,
                    ),
                    types.Match(
                        6,
                        types.Option("two", 12, True, None),
                        types.Option("three", 16, False, None),
                        1,
                    ),
                ],
            ),
            types.Round(
                "Final",
                [
                    types.Match(
                        7,
                        types.Option("one", 16, True, None),
                        types.Option("two", 32, False, None),
                        0,
                    )
                ],
            ),
        ],
    )

    result = flatten_bracket(tournament)

    # Round 1: 8 slots, bracket order [0,7,3,4,1,6,2,5]
    # place=0 → index 0: (one, eight)
    # place=3 → index 2: (four, five)
    # place=1 → index 4: (two, seven)
    # place=2 → index 6: (three, six)
    assert result == [
        [
            Box("one", 1, True),
            Box("eight", 2, False),
            Box("four", 3, True),
            Box("five", 4, False),
            Box("two", 5, True),
            Box("seven", 6, False),
            Box("three", 7, True),
            Box("six", 8, False),
        ],
        # Round 2: 4 slots, bracket order [0,3,1,2]
        # place=0 → index 0: (one, four)
        # place=1 → index 2: (two, three)
        [
            Box("one", 4, True),
            Box("four", 8, False),
            Box("two", 12, True),
            Box("three", 16, False),
        ],
        # Final: 2 slots
        [Box("one", 16, True), Box("two", 32, False)],
        # Champion
        [Box("one", None, True)],
    ]


def test_6_option_with_play_in():
    """Test 6-option tournament with play-in (4+2).

    Tournament size: 4
    Play-in matches: 2 (seeds 3,4,5,6)
    Bracket order for 4: [0, 3, 1, 2]

    Play-in:
    - Match place=2 (seed 3 vs 6) → index 1 in bracket order → slots 2-3 in doubled layout
    - Match place=3 (seed 4 vs 5) → index 0 in bracket order → slots 0-1 in doubled layout
    """
    tournament = types.Tournament(
        1,
        [
            types.Round(
                "Play-in round",
                [
                    types.Match(
                        1,
                        types.Option("four", 5, True, None),
                        types.Option("five", 6, False, None),
                        3,
                    ),
                    types.Match(
                        2,
                        types.Option("three", 7, True, None),
                        types.Option("six", 8, False, None),
                        2,
                    ),
                ],
            ),
            types.Round(
                "Round 1",
                [
                    types.Match(
                        3, types.Option("one", 1, True, 1), types.Option("four", 2, False, 1), 0
                    ),
                    types.Match(
                        4, types.Option("two", 3, True, 2), types.Option("three", 4, False, 2), 1
                    ),
                ],
            ),
            types.Round(
                "Final",
                [
                    types.Match(
                        5, types.Option("one", 10, True, 3), types.Option("two", 12, False, 4), 0
                    )
                ],
            ),
        ],
    )

    result = flatten_bracket(tournament)

    # Play-in: 8 slots (tournament_size * 2 = 4 * 2)
    # place=3 → index 1 in [0,3,1,2] → slots 2,3: (four, five)
    # place=2 → index 3 in [0,3,1,2] → slots 6,7: (three, six)
    # Byes at indices 0,2 → slots 0,1,4,5
    assert result == [
        [
            None,
            None,
            Box("four", 5, True),
            Box("five", 6, False),
            None,
            None,
            Box("three", 7, True),
            Box("six", 8, False),
        ],
        # Round 1: 4 slots, bracket order [0,3,1,2]
        [
            Box("one", 1, True),
            Box("four", 2, False),
            Box("two", 3, True),
            Box("three", 4, False),
        ],
        # Final
        [Box("one", 10, True), Box("two", 12, False)],
        # Champion
        [Box("one", None, True)],
    ]


def test_unfinished_tournament():
    """Test tournament that's only partially complete."""
    tournament = types.Tournament(
        1,
        [
            types.Round(
                "Round 1",
                [
                    types.Match(
                        1,
                        types.Option("one", 1, True, None),
                        types.Option("four", 2, False, None),
                        0,
                    ),
                    types.Match(
                        2,
                        types.Option("two", None, False, None),
                        types.Option("three", None, False, None),
                        1,
                    ),
                ],
            ),
        ],
    )

    result = flatten_bracket(tournament)

    assert result == [
        [
            Box("one", 1, True),
            Box("four", 2, False),
            Box("two", None, False),
            Box("three", None, False),
        ],
        # Future rounds are empty
        [Box("", None, False), Box("", None, False)],
        [Box("", None, False)],
    ]


def test_empty_tournament_raises_error():
    """Test that empty tournament raises error."""
    tournament = types.Tournament(1, [])

    with pytest.raises(ValueError, match="Tournament has no rounds"):
        flatten_bracket(tournament)


def test_widen_bracket():
    """Test widen_bracket splits rounds into left/right halves."""
    flat = [
        [Box("a", 1, False), Box("b", 2, True), Box("c", 3, False), Box("d", 4, True)],
        [Box("b", 5, False), Box("d", 6, True)],
        [Box("d", None, True)],
    ]

    wide = widen_bracket(flat)

    # Left halves
    assert wide[0] == [Box("a", 1, False), Box("b", 2, True)]  # First half of round 1
    assert wide[1] == [Box("b", 5, False)]  # First half of round 2
    # Champion in middle
    assert wide[2] == [Box("d", None, True)]
    # Right halves (reversed)
    assert wide[3] == [Box("d", 6, True)]  # Second half of round 2
    assert wide[4] == [Box("c", 3, False), Box("d", 4, True)]  # Second half of round 1


def test_widen_with_play_in():
    """Test widen_bracket with play-in round."""
    flat = [
        # Play-in (with Nones for byes)
        [None, None, Box("five", 5, False), Box("six", 6, True)],
        # Round 1
        [Box("one", 1, False), Box("two", 2, True), Box("three", 3, False), Box("six", 7, True)],
        # Final
        [Box("two", 10, False), Box("six", 12, True)],
        # Champion
        [Box("six", None, True)],
    ]

    wide = widen_bracket(flat)

    assert wide == [
        [None, None],  # Left half of play-in
        [Box("one", 1, False), Box("two", 2, True)],  # Left half of round 1
        [Box("two", 10, False)],  # Left half of final
        [Box("six", None, True)],  # Champion
        [Box("six", 12, True)],  # Right half of final
        [Box("three", 3, False), Box("six", 7, True)],  # Right half of round 1
        [Box("five", 5, False), Box("six", 6, True)],  # Right half of play-in
    ]


def test_widen_empty():
    """Test widen_bracket with empty input."""
    assert widen_bracket([]) == []
