#!/usr/bin/env python3
"""Debug height calculation."""
from discord_brackets import types
from discord_brackets.visualization.layout import flatten_bracket, widen_bracket
from discord_brackets.visualization.render import _calculate_bracket_positions, BOX_HEIGHT, MARGIN

# Simple 8-option tournament
tournament = types.Tournament(
    1,
    [
        types.Round("Round 1", [
            types.Match(1, types.Option("A", 1, True, None), types.Option("B", 2, False, None)),
            types.Match(2, types.Option("C", 3, True, None), types.Option("D", 4, False, None)),
            types.Match(3, types.Option("E", 5, True, None), types.Option("F", 6, False, None)),
            types.Match(4, types.Option("G", 7, True, None), types.Option("H", 8, False, None)),
        ]),
        types.Round("Round 2", [
            types.Match(5, types.Option("A", 9, True, 1), types.Option("C", 10, False, 2)),
            types.Match(6, types.Option("E", 11, True, 3), types.Option("G", 12, False, 4)),
        ]),
        types.Round("Finals", [
            types.Match(7, types.Option("A", 13, True, 5), types.Option("E", 14, False, 6)),
        ]),
    ],
)

# Get layout
flat = flatten_bracket(tournament)
wide = widen_bracket(flat)

# Calculate positions
columns = wide
is_all_none = [all(item is None for item in col) for col in columns]
column_widths = [120.0] * len(columns)  # Use default width

positions = _calculate_bracket_positions(columns, is_all_none, column_widths)

# Print all y positions
print("All y positions:")
for col_idx, col_positions in enumerate(positions):
    if col_positions is not None:
        print(f"Column {col_idx}: {[y for x, y in col_positions]}")

# Calculate max_y as the code does
max_y = max(pos[1] + BOX_HEIGHT for col_positions in positions if col_positions is not None for pos in col_positions)
print(f"\nCalculated max_y: {max_y}")
print(f"Height would be: {max_y + MARGIN}")

# Find actual max
actual_max = max(pos[1] for col_positions in positions if col_positions is not None for pos in col_positions)
print(f"Actual max y (without BOX_HEIGHT): {actual_max}")
print(f"With BOX_HEIGHT added: {actual_max + BOX_HEIGHT}")
