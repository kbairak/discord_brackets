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
                types.Match(1, types.Option("Alice", 10, False), types.Option("Bob", 15, True), 0),
                types.Match(2, types.Option("Carl", 10, False), types.Option("Dave", 15, True), 1),
            ],
        ),
        types.Round(
            "Final",
            [
                types.Match(3, types.Option("Bob", 10, False), types.Option("Dave", 15, False), 0),
            ],
        ),
    ],
)

# =============================================================================
# RENDER AND PREVIEW
# =============================================================================

if __name__ == "__main__":
    # Generate SVG
    svg = render_bracket_svg(tournament)

    # Save to /tmp
    svg_path = Path("/tmp/bracket_preview.svg")
    svg_path.write_text(svg, encoding="utf-8")

    webbrowser.open(f"file://{svg_path.absolute()}")

    print(f"✓ Saved to {svg_path}")
    print("✓ Opened in browser")
    print()
    print("Edit the tournament definition in this file and re-run to see changes!")
