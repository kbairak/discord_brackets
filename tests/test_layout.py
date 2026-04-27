from __future__ import annotations

import pytest

from discord_brackets import types
from discord_brackets.visualization.layout import Box, flatten_bracket


def test_4_option_tournament():
    """Test simpler 4-option tournament."""
    tournament = types.Tournament(
        2,
        [
            types.Round(
                "types.Round 1",
                [
                    types.Match(1, types.Option("alice", 10, True), types.Option("bob", 5, False)),
                    types.Match(
                        2, types.Option("charlie", 7, False), types.Option("diana", 12, True)
                    ),
                ],
            ),
            types.Round(
                "Final",
                [
                    types.Match(
                        3, types.Option("alice", 20, False), types.Option("diana", 25, True)
                    )
                ],
            ),
        ],
    )

    result = flatten_bracket(tournament)

    assert result == [
        [
            Box("alice", 10, True),
            Box("bob", 5, False),
            Box("charlie", 7, False),
            Box("diana", 12, True),
        ],
        [Box("alice", 20, False), Box("diana", 25, True)],
        [Box("diana", None, True)],
    ]


def test_basic_8_option_tournament():
    """Test basic 8-option tournament with all matches completed."""
    # types.Round 1: 4 matches
    tournament = types.Tournament(
        1,
        [
            types.Round(
                "types.Round 1",
                [
                    types.Match(1, types.Option("one", 1, False), types.Option("two", 2, True)),
                    types.Match(2, types.Option("three", 3, False), types.Option("four", 4, True)),
                    types.Match(3, types.Option("five", 5, False), types.Option("six", 6, True)),
                    types.Match(
                        4, types.Option("seven", 7, False), types.Option("eight", 8, True)
                    ),
                ],
            ),
            # types.Round 2: 2 matches (winners from round 1)
            types.Round(
                "types.Round 2",
                [
                    types.Match(5, types.Option("two", 4, False), types.Option("four", 8, True)),
                    types.Match(
                        6, types.Option("six", 12, False), types.Option("eight", 16, True)
                    ),
                ],
            ),
            # types.Round 3 (Final): 1 match
            types.Round(
                "Final",
                [types.Match(7, types.Option("four", 16, False), types.Option("eight", 32, True))],
            ),
        ],
    )

    result = flatten_bracket(tournament)

    assert result == [
        [
            Box("one", 1, False),
            Box("two", 2, True),
            Box("three", 3, False),
            Box("four", 4, True),
            Box("five", 5, False),
            Box("six", 6, True),
            Box("seven", 7, False),
            Box("eight", 8, True),
        ],
        [
            Box("two", 4, False),
            Box("four", 8, True),
            Box("six", 12, False),
            Box("eight", 16, True),
        ],
        [Box("four", 16, False), Box("eight", 32, True)],
        [Box("eight", None, True)],
    ]


def test_16_option_tournament():
    """Test larger 16-option tournament."""
    # Build 16-option tournament (types.Round 1: 8 matches, types.Round 2: 4, types.Round 3: 2, types.Round 4: 1, Final: champion)
    round1_matches = [
        types.Match(
            i,
            types.Option(f"p{i * 2}", i * 2, False),
            types.Option(f"p{i * 2 + 1}", i * 2 + 1, True),
        )
        for i in range(8)
    ]

    round2_matches = [
        types.Match(
            8 + i,
            types.Option(f"p{i * 2 + 1}", 10 + i * 2, False),
            types.Option(f"p{i * 2 + 3}", 10 + i * 2 + 1, True),
        )
        for i in range(4)
    ]

    round3_matches = [
        types.Match(
            12 + i,
            types.Option(f"p{i * 4 + 3}", 20 + i * 2, False),
            types.Option(f"p{i * 4 + 7}", 20 + i * 2 + 1, True),
        )
        for i in range(2)
    ]

    final_match = types.Match(14, types.Option("p7", 30, False), types.Option("p15", 31, True))

    tournament = types.Tournament(
        3,
        [
            types.Round("types.Round 1", round1_matches),
            types.Round("types.Round 2", round2_matches),
            types.Round("types.Round 3", round3_matches),
            types.Round("Final", [final_match]),
        ],
    )

    result = flatten_bracket(tournament)

    assert result == [
        [
            Box("p0", 0, False),
            Box("p1", 1, True),
            Box("p2", 2, False),
            Box("p3", 3, True),
            Box("p4", 4, False),
            Box("p5", 5, True),
            Box("p6", 6, False),
            Box("p7", 7, True),
            Box("p8", 8, False),
            Box("p9", 9, True),
            Box("p10", 10, False),
            Box("p11", 11, True),
            Box("p12", 12, False),
            Box("p13", 13, True),
            Box("p14", 14, False),
            Box("p15", 15, True),
        ],
        [
            Box("p1", 10, False),
            Box("p3", 11, True),
            Box("p3", 12, False),
            Box("p5", 13, True),
            Box("p5", 14, False),
            Box("p7", 15, True),
            Box("p7", 16, False),
            Box("p9", 17, True),
        ],
        [Box("p3", 20, False), Box("p7", 21, True), Box("p7", 22, False), Box("p11", 23, True)],
        [Box("p7", 30, False), Box("p15", 31, True)],
        [Box("p15", None, True)],
    ]


def test_incomplete_final_match():
    """Test that incomplete tournament (no winner in final match) returns empty champion box."""
    tournament = types.Tournament(
        4,
        [
            types.Round(
                "Final",
                [types.Match(1, types.Option("alice", 10, False), types.Option("bob", 5, False))],
            )
        ],
    )

    result = flatten_bracket(tournament)

    # Final match has votes but no winner yet - should show names and votes
    assert result == [[Box("alice", 10, False), Box("bob", 5, False)], [Box("", None, False)]]


def test_empty_tournament_raises_error():
    """Test that empty tournament raises ValueError."""
    tournament = types.Tournament(5, [])

    with pytest.raises(ValueError, match="Tournament has no rounds"):
        flatten_bracket(tournament)


def test_champion_votes_none():
    """Test that only the champion (last box) has None."""
    tournament = types.Tournament(
        6,
        [
            types.Round(
                "Final",
                [
                    types.Match(
                        1, types.Option("winner", 100, True), types.Option("loser", 50, False)
                    )
                ],
            )
        ],
    )

    result = flatten_bracket(tournament)

    # Final round should have original votes
    assert result == [
        [Box("winner", 100, True), Box("loser", 50, False)],
        [Box("winner", None, True)],
    ]


def test_unfinished_tournament_round_1_only():
    """Test unfinished tournament with only types.Round 1 completed."""
    tournament = types.Tournament(
        7,
        [
            types.Round(
                "types.Round 1",
                [
                    types.Match(1, types.Option("one", 1, False), types.Option("two", 2, True)),
                    types.Match(2, types.Option("three", 3, False), types.Option("four", 4, True)),
                    types.Match(3, types.Option("five", 5, False), types.Option("six", 6, True)),
                    types.Match(
                        4, types.Option("seven", 7, False), types.Option("eight", 8, True)
                    ),
                ],
            )
        ],
    )

    result = flatten_bracket(tournament)

    assert result == [
        [
            Box("one", 1, False),
            Box("two", 2, True),
            Box("three", 3, False),
            Box("four", 4, True),
            Box("five", 5, False),
            Box("six", 6, True),
            Box("seven", 7, False),
            Box("eight", 8, True),
        ],
        [Box("", None, False), Box("", None, False), Box("", None, False), Box("", None, False)],
        [Box("", None, False), Box("", None, False)],
        [Box("", None, False)],
    ]


def test_unfinished_tournament_round_2_not_voted():
    """Test tournament with types.Round 2 matches created but not voted on."""
    tournament = types.Tournament(
        8,
        [
            types.Round(
                "types.Round 1",
                [
                    types.Match(1, types.Option("one", 1, False), types.Option("two", 2, True)),
                    types.Match(2, types.Option("three", 3, False), types.Option("four", 4, True)),
                ],
            ),
            types.Round(
                "types.Round 2",
                [
                    types.Match(
                        3, types.Option("two", None, False), types.Option("four", None, False)
                    )
                ],
            ),
        ],
    )

    result = flatten_bracket(tournament)

    assert result == [
        [Box("one", 1, False), Box("two", 2, True), Box("three", 3, False), Box("four", 4, True)],
        [Box("two", None, False), Box("four", None, False)],
        [Box("", None, False)],
    ]


def test_unfinished_tournament_partial_rounds():
    """Test tournament with types.Round 1 complete and types.Round 2 partially complete."""
    tournament = types.Tournament(
        9,
        [
            types.Round(
                "types.Round 1",
                [
                    types.Match(1, types.Option("one", 1, False), types.Option("two", 2, True)),
                    types.Match(2, types.Option("three", 3, False), types.Option("four", 4, True)),
                    types.Match(3, types.Option("five", 5, False), types.Option("six", 6, True)),
                    types.Match(
                        4, types.Option("seven", 7, False), types.Option("eight", 8, True)
                    ),
                ],
            ),
            types.Round(
                "types.Round 2",
                [
                    types.Match(5, types.Option("two", 10, True), types.Option("four", 5, False)),
                    types.Match(
                        6, types.Option("six", None, False), types.Option("eight", None, False)
                    ),
                ],
            ),
        ],
    )

    result = flatten_bracket(tournament)

    assert result == [
        [
            Box("one", 1, False),
            Box("two", 2, True),
            Box("three", 3, False),
            Box("four", 4, True),
            Box("five", 5, False),
            Box("six", 6, True),
            Box("seven", 7, False),
            Box("eight", 8, True),
        ],
        [
            Box("two", 10, True),
            Box("four", 5, False),
            Box("six", None, False),
            Box("eight", None, False),
        ],
        [Box("", None, False), Box("", None, False)],
        [Box("", None, False)],
    ]


def test_play_in_10_option_tournament():
    """Test 10-option tournament with play-in round (8+2)."""
    tournament = types.Tournament(
        10,
        [
            types.Round(
                "Play-in round",
                [
                    types.Match(1, types.Option("nine", 9, False), types.Option("ten", 10, True)),
                    types.Match(
                        2, types.Option("seven", 7, False), types.Option("eight", 8, True)
                    ),
                ],
            ),
            types.Round(
                "Round 1",
                [
                    types.Match(3, types.Option("one", 1, False), types.Option("two", 2, True)),
                    types.Match(4, types.Option("three", 3, False), types.Option("four", 4, True)),
                    types.Match(5, types.Option("five", 5, False), types.Option("six", 6, True)),
                    types.Match(6, types.Option("ten", 11, True), types.Option("eight", 9, False)),
                ],
            ),
            types.Round(
                "Round 2",
                [
                    types.Match(7, types.Option("two", 12, False), types.Option("four", 14, True)),
                    types.Match(8, types.Option("six", 13, False), types.Option("ten", 15, True)),
                ],
            ),
            types.Round(
                "Final",
                [types.Match(9, types.Option("four", 20, False), types.Option("ten", 22, True))],
            ),
        ],
    )

    result = flatten_bracket(tournament)

    assert result == [
        # Play-in: 12 None (for 16-slot structure) + 2 matches (4 boxes)
        [
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            Box("nine", 9, False),
            Box("ten", 10, True),
            Box("seven", 7, False),
            Box("eight", 8, True),
        ],
        # Round 1: 8 boxes
        [
            Box("one", 1, False),
            Box("two", 2, True),
            Box("three", 3, False),
            Box("four", 4, True),
            Box("five", 5, False),
            Box("six", 6, True),
            Box("ten", 11, True),
            Box("eight", 9, False),
        ],
        # Round 2: 4 boxes
        [
            Box("two", 12, False),
            Box("four", 14, True),
            Box("six", 13, False),
            Box("ten", 15, True),
        ],
        # Final: 2 boxes
        [Box("four", 20, False), Box("ten", 22, True)],
        # Champion
        [Box("ten", None, True)],
    ]


def test_play_in_6_option_tournament():
    """Test 6-option tournament with play-in round (4+2)."""
    tournament = types.Tournament(
        11,
        [
            types.Round(
                "Play-in round",
                [types.Match(1, types.Option("five", 5, False), types.Option("six", 6, True))],
            ),
            types.Round(
                "Round 1",
                [
                    types.Match(2, types.Option("one", 1, False), types.Option("two", 2, True)),
                    types.Match(3, types.Option("three", 3, False), types.Option("six", 7, True)),
                ],
            ),
            types.Round(
                "Final",
                [types.Match(4, types.Option("two", 10, False), types.Option("six", 12, True))],
            ),
        ],
    )

    result = flatten_bracket(tournament)

    assert result == [
        # Play-in: 6 None (for 8-slot structure) + 1 match (2 boxes)
        [None, None, None, None, None, None, Box("five", 5, False), Box("six", 6, True)],
        # Round 1: 4 boxes
        [Box("one", 1, False), Box("two", 2, True), Box("three", 3, False), Box("six", 7, True)],
        # Final: 2 boxes
        [Box("two", 10, False), Box("six", 12, True)],
        # Champion
        [Box("six", None, True)],
    ]


def test_play_in_unfinished():
    """Test unfinished tournament with play-in complete but Round 1 not voted."""
    tournament = types.Tournament(
        12,
        [
            types.Round(
                "Play-in round",
                [types.Match(1, types.Option("five", 5, False), types.Option("six", 6, True))],
            ),
            types.Round(
                "Round 1",
                [
                    types.Match(
                        2, types.Option("one", None, False), types.Option("two", None, False)
                    ),
                    types.Match(
                        3, types.Option("three", None, False), types.Option("six", None, False)
                    ),
                ],
            ),
        ],
    )

    result = flatten_bracket(tournament)

    assert result == [
        # Play-in: completed (6 Nones for 8-slot structure + 1 match)
        [None, None, None, None, None, None, Box("five", 5, False), Box("six", 6, True)],
        # Round 1: matches exist but no votes
        [
            Box("one", None, False),
            Box("two", None, False),
            Box("three", None, False),
            Box("six", None, False),
        ],
        # Final: doesn't exist
        [Box("", None, False), Box("", None, False)],
        # Champion: doesn't exist
        [Box("", None, False)],
    ]


def test_widen_8_option_tournament():
    """Test widen_bracket for 8-option tournament."""
    from discord_brackets.visualization.layout import widen_bracket

    # Flat layout for 8-option tournament
    flat = [
        [
            Box("one", 1, False),
            Box("two", 2, True),
            Box("three", 3, False),
            Box("four", 4, True),
            Box("five", 5, False),
            Box("six", 6, True),
            Box("seven", 7, False),
            Box("eight", 8, True),
        ],
        [
            Box("two", 4, False),
            Box("four", 8, True),
            Box("six", 12, False),
            Box("eight", 16, True),
        ],
        [Box("four", 16, False), Box("eight", 32, True)],
        [Box("eight", None, True)],
    ]

    wide = widen_bracket(flat)

    assert wide == [
        # Left halves
        [Box("one", 1, False), Box("two", 2, True), Box("three", 3, False), Box("four", 4, True)],
        [Box("two", 4, False), Box("four", 8, True)],
        [Box("four", 16, False)],
        # Champion
        [Box("eight", None, True)],
        # Right halves (reversed)
        [Box("eight", 32, True)],
        [Box("six", 12, False), Box("eight", 16, True)],
        [
            Box("five", 5, False),
            Box("six", 6, True),
            Box("seven", 7, False),
            Box("eight", 8, True),
        ],
    ]


def test_widen_10_option_with_play_in():
    """Test widen_bracket for 10-option tournament with play-in."""
    from discord_brackets.visualization.layout import widen_bracket

    # Flat layout for 10-option tournament
    flat = [
        [
            None,
            None,
            None,
            None,
            Box("nine", 9, False),
            Box("ten", 10, True),
            Box("seven", 7, False),
            Box("eight", 8, True),
        ],
        [
            Box("one", 1, False),
            Box("two", 2, True),
            Box("three", 3, False),
            Box("four", 4, True),
            Box("five", 5, False),
            Box("six", 6, True),
            Box("ten", 11, True),
            Box("eight", 9, False),
        ],
        [
            Box("two", 12, False),
            Box("four", 14, True),
            Box("six", 13, False),
            Box("ten", 15, True),
        ],
        [Box("four", 20, False), Box("ten", 22, True)],
        [Box("ten", None, True)],
    ]

    wide = widen_bracket(flat)

    assert wide == [
        # Left halves
        [None, None, None, None],  # All-None column preserved
        [Box("one", 1, False), Box("two", 2, True), Box("three", 3, False), Box("four", 4, True)],
        [Box("two", 12, False), Box("four", 14, True)],
        [Box("four", 20, False)],
        # Champion
        [Box("ten", None, True)],
        # Right halves (reversed)
        [Box("ten", 22, True)],
        [Box("six", 13, False), Box("ten", 15, True)],
        [Box("five", 5, False), Box("six", 6, True), Box("ten", 11, True), Box("eight", 9, False)],
        [
            Box("nine", 9, False),
            Box("ten", 10, True),
            Box("seven", 7, False),
            Box("eight", 8, True),
        ],
    ]


def test_widen_4_option_tournament():
    """Test widen_bracket for 4-option tournament."""
    from discord_brackets.visualization.layout import widen_bracket

    flat = [
        [
            Box("alice", 10, True),
            Box("bob", 5, False),
            Box("charlie", 7, False),
            Box("diana", 12, True),
        ],
        [Box("alice", 20, False), Box("diana", 25, True)],
        [Box("diana", None, True)],
    ]

    wide = widen_bracket(flat)

    assert wide == [
        [Box("alice", 10, True), Box("bob", 5, False)],
        [Box("alice", 20, False)],
        [Box("diana", None, True)],
        [Box("diana", 25, True)],
        [Box("charlie", 7, False), Box("diana", 12, True)],
    ]


def test_widen_empty():
    """Test widen_bracket with empty input."""
    from discord_brackets.visualization.layout import widen_bracket

    assert widen_bracket([]) == []
