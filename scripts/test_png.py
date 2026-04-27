#!/usr/bin/env python3
"""Test PNG conversion with cairosvg."""

import re
import webbrowser
from pathlib import Path
from typing import cast

import cairosvg

from discord_brackets import types
from discord_brackets.visualization.render import render_bracket_svg

# Simple tournament with Greek names
tournament = types.Tournament(
    1,
    [
        types.Round(
            "Round 1",
            [types.Match(1, types.Option("Alice", 10, False), types.Option("Bob", 15, True), 0)],
        )
    ],
)

# Generate SVG
if __name__ == "__main__":
    svg = render_bracket_svg(tournament)

    # Save SVG
    svg_path = Path("/tmp/bracket_test.svg")
    svg_path.write_text(svg)

    # Extract viewBox dimensions
    viewbox_match = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
    if viewbox_match:
        width, height = viewbox_match.groups()
        print(f"SVG viewBox: {width} x {height}")

    # Convert to PNG
    png_bytes = cairosvg.svg2png(bytestring=svg.encode("utf-8"))
    png_bytes = cast(bytes, png_bytes)

    # Save PNG
    png_path = Path("/tmp/bracket_test.png")
    png_path.write_bytes(png_bytes)

    webbrowser.open(f"file://{png_path.absolute()}")

    print(f"✓ Saved SVG to {svg_path}")
    print(f"✓ Saved PNG to {png_path} ({len(png_bytes)} bytes)")
    print()
    print("Edit the tournament definition in this file and re-run to see changes!")
