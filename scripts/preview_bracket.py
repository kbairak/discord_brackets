#!/usr/bin/env python3
"""Preview script for rapid SVG bracket development.

Modify the tournament definition below, then run:
    python scripts/preview_bracket.py

The SVG will be saved to /tmp/bracket_preview.svg and opened in your browser.
"""

import webbrowser
from pathlib import Path

from discord_brackets import types
from discord_brackets.visualization.render import render_bracket_svg

# =============================================================================
# MODIFY THIS TOURNAMENT TO TEST DIFFERENT SCENARIOS
# =============================================================================

# Example 1: 8-option completed tournament
tournament = types.Tournament(
    1,
    [
        types.Round(
            "Round 1",
            [
                types.Match(1, types.Option("Alice", 10, False), types.Option("Bob", 15, True)),
                types.Match(2, types.Option("Charlie", 8, False), types.Option("Diana", 12, True)),
                types.Match(3, types.Option("Eve", 9, False), types.Option("Frank", 14, True)),
                types.Match(4, types.Option("Grace", 7, False), types.Option("Henry", 11, True)),
            ],
        ),
        types.Round(
            "Round 2",
            [
                types.Match(5, types.Option("Bob", 20, False), types.Option("Diana", 25, True)),
                types.Match(6, types.Option("Frank", 18, False), types.Option("Henry", 22, True)),
            ],
        ),
        types.Round(
            "Final",
            [types.Match(7, types.Option("Diana", 30, False), types.Option("Henry", 35, True))],
        ),
    ],
)


# Example 2: 10-option tournament with play-in (commented out)
# tournament = types.Tournament(
#     2,
#     [
#         types.Round(
#             "Play-in round",
#             [
#                 types.Match(1, types.Option("Player9", 5, False), types.Option("Player10", 8, True)),
#                 types.Match(2, types.Option("Player7", 6, False), types.Option("Player8", 7, True)),
#             ],
#         ),
#         types.Round(
#             "Round 1",
#             [
#                 types.Match(3, types.Option("Player1", 10, False), types.Option("Player2", 12, True)),
#                 types.Match(4, types.Option("Player3", 9, False), types.Option("Player4", 11, True)),
#                 types.Match(5, types.Option("Player5", 8, False), types.Option("Player6", 13, True)),
#                 types.Match(6, types.Option("Player10", 14, True), types.Option("Player8", 7, False)),
#             ],
#         ),
#         types.Round(
#             "Round 2",
#             [
#                 types.Match(7, types.Option("Player2", 15, False), types.Option("Player4", 18, True)),
#                 types.Match(8, types.Option("Player6", 16, False), types.Option("Player10", 20, True)),
#             ],
#         ),
#         types.Round(
#             "Final",
#             [types.Match(9, types.Option("Player4", 25, False), types.Option("Player10", 30, True))],
#         ),
#     ],
# )

# Example 3: Unfinished tournament (commented out)
# tournament = types.Tournament(
#     3,
#     [
#         types.Round(
#             "Round 1",
#             [
#                 types.Match(1, types.Option("TeamA", 10, True), types.Option("TeamB", 5, False)),
#                 types.Match(2, types.Option("TeamC", 8, False), types.Option("TeamD", 12, True)),
#             ],
#         ),
#         types.Round(
#             "Final",
#             [
#                 types.Match(3, types.Option("TeamA", None, False), types.Option("TeamD", None, False)),
#             ],
#         ),
#     ],
# )

# =============================================================================
# RENDER AND PREVIEW
# =============================================================================

if __name__ == "__main__":
    # Generate SVG
    svg = render_bracket_svg(tournament)

    # Save to /tmp
    svg_path = Path("/tmp/bracket_preview.svg")
    svg_path.write_text(svg, encoding="utf-8")

    # Open in default browser
    browser = webbrowser.get()
    browser.open(f"file://{svg_path.absolute()}")

    print(f"✓ Saved to {svg_path}")
    print("✓ Opened in browser")
    print()
    print("Edit the tournament definition in this file and re-run to see changes!")
