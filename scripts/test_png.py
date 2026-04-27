#!/usr/bin/env python3
"""Test PNG conversion with cairosvg."""
import cairosvg
import re
from pathlib import Path

from discord_brackets import types
from discord_brackets.visualization.render import render_bracket_svg

# Simple tournament with Greek names
tournament = types.Tournament(
    1,
    [
        types.Round(
            "Finals",
            [
                types.Match(
                    1,
                    types.Option("Alice", 10, True, None),
                    types.Option("Bob", 5, False, None),
                ),
            ],
        ),
        types.Round(
            "Semifinals",
            [
                types.Match(
                    2,
                    types.Option("Alice", 8, True, 0),
                    types.Option("Κωνσταντίνος", 3, False, 0),
                ),
                types.Match(
                    3,
                    types.Option("Bob", 7, True, 0),
                    types.Option("Αλέξανδρος", 4, False, 0),
                ),
            ],
        ),
    ],
)

# Generate SVG
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

# Save PNG
png_path = Path("/tmp/bracket_test.png")
png_path.write_bytes(png_bytes)

print(f"✓ Saved SVG to {svg_path}")
print(f"✓ Saved PNG to {png_path} ({len(png_bytes)} bytes)")
print("✓ Greek names: Κωνσταντίνος, Αλέξανδρος")
print("\nOpen the SVG in a browser to check if it's cropped there too.")
