from __future__ import annotations

import io

import discord

from discord_brackets import db
from discord_brackets.types import Tournament
from discord_brackets.utils import split_emoji
from discord_brackets.visualization.layout import Box, flatten_bracket, widen_bracket

# Visual constants
BOX_HEIGHT = 35
BOX_WIDTH = 120
VERTICAL_GAP = 15
COLUMN_SPACING = 60
MARGIN = 50
MAX_NAME_LENGTH = 25


def render_bracket_svg(tournament: Tournament) -> str:
    """Generate SVG string from tournament.

    Args:
        tournament: Tournament to render

    Returns:
        SVG string ready for display or saving
    """
    # Get layout
    flat = flatten_bracket(tournament)
    wide = widen_bracket(flat)

    # Keep all columns, but track which are all-None (for positioning)
    columns = wide
    is_all_none = [all(item is None for item in col) for col in columns]

    if all(is_all_none):
        return _empty_svg()

    # Calculate width for each column based on longest name in that column
    column_widths: list[float] = []
    for col in columns:
        max_len = 0
        for box in col:
            if box and box.name:
                _, name_text = split_emoji(box.name)
                # Account for vote count " (999)"
                display_length = len(name_text) + (6 if box.votes is not None else 0)
                max_len = max(max_len, display_length)
        # 8px per character, min 120px, max 250px
        col_width = min(250, max(120, max_len * 8))
        column_widths.append(col_width)

    # Calculate positions for each box based on bracket structure
    positions = _calculate_bracket_positions(columns, is_all_none, column_widths)

    # Calculate dimensions (only count non-None columns for width)
    total_width = sum(column_widths[i] for i in range(len(columns)) if not is_all_none[i])
    visible_columns = sum(1 for none in is_all_none if not none)
    max_y = max(pos[1] + BOX_HEIGHT for col_positions in positions if col_positions is not None for pos in col_positions)
    width = MARGIN * 2 + total_width + (visible_columns - 1) * COLUMN_SPACING
    height = max_y + MARGIN * 2  # Extra margin at bottom to prevent cropping

    # Build SVG
    parts = [_svg_header(width, height)]

    # Draw boxes and connectors
    for col_idx, column in enumerate(columns):
        # Skip all-None columns for rendering (but we still calculated positions for them)
        if is_all_none[col_idx]:
            continue

        col_positions = positions[col_idx]
        box_width = column_widths[col_idx]

        for box_idx, box in enumerate(column):
            if box is None:
                continue

            x, y = col_positions[box_idx]

            # Check if this is the champion (middle column, single box)
            is_champion = len(column) == 1 and col_idx == len(columns) // 2

            # Draw box
            parts.append(_draw_box(x, y, box, is_champion, box_width))

            # Draw connector to next column if not last column
            # Skip connectors to all-None columns
            if col_idx < len(columns) - 1 and not is_all_none[col_idx + 1]:
                next_column = columns[col_idx + 1]
                next_positions = positions[col_idx + 1]

                # Determine which boxes in next column this connects to
                if len(next_column) < len(column):
                    # Merging: 2 boxes → 1 box
                    # This box connects to next_column[box_idx // 2]
                    next_box_idx = box_idx // 2
                    if next_box_idx < len(next_column) and next_column[next_box_idx] is not None:
                        next_x, next_y = next_positions[next_box_idx]
                        parts.append(_draw_bracket_connector(x, y, next_x, next_y, box_width))
                elif len(next_column) > len(column):
                    # Expanding: 1 box → 2 boxes
                    # This box connects to next_column[box_idx * 2] and next_column[box_idx * 2 + 1]
                    child_idx_1 = box_idx * 2
                    child_idx_2 = box_idx * 2 + 1

                    if child_idx_1 < len(next_column) and next_column[child_idx_1] is not None:
                        next_x, next_y = next_positions[child_idx_1]
                        parts.append(_draw_bracket_connector(x, y, next_x, next_y, box_width))

                    if child_idx_2 < len(next_column) and next_column[child_idx_2] is not None:
                        next_x, next_y = next_positions[child_idx_2]
                        parts.append(_draw_bracket_connector(x, y, next_x, next_y, box_width))
                else:
                    # Same size: 1 box → 1 box
                    if box_idx < len(next_column) and next_column[box_idx] is not None:
                        next_x, next_y = next_positions[box_idx]
                        parts.append(_draw_bracket_connector(x, y, next_x, next_y, box_width))

    parts.append("</svg>")
    return "".join(parts)


def _calculate_bracket_positions(
    columns: list[list[Box | None]],
    is_all_none: list[bool],
    column_widths: list[float],
) -> list[list[tuple[float, float]]]:
    """Calculate (x, y) positions for each box maintaining bracket structure.

    Boxes should be vertically aligned such that when 2 boxes merge to 1,
    the resulting box is centered between its parents.

    All-None columns are given zero width (same x as next visible column).
    """
    # Helper function to calculate x position for a column index
    # Accounts for zero-width all-None columns and variable column widths
    def get_column_x(col_idx: int) -> float:
        x = MARGIN
        for i in range(col_idx):
            if not is_all_none[i]:
                x += column_widths[i] + COLUMN_SPACING
        return x

    # Find champion column (has 1 box)
    champion_col_idx = next(
        (i for i, col in enumerate(columns) if len(col) == 1), len(columns) // 2
    )

    # Calculate positions from both sides towards the middle
    positions: list[list[tuple[float, float]] | None] = [None] * len(columns)

    # Calculate total height needed for outer columns to determine vertical centering
    # Use the larger of the two outer columns
    first_column = columns[0]
    last_column = columns[-1]
    max_outer_boxes = max(len(first_column), len(last_column))
    outer_column_height = max_outer_boxes * (BOX_HEIGHT + VERTICAL_GAP) - VERTICAL_GAP

    # Calculate vertical offset to center the bracket
    # We want the champion to be in the vertical center
    vertical_offset = MARGIN

    # Calculate leftmost column - evenly spaced
    first_positions: list[tuple[float, float]] = []
    for box_idx in range(len(first_column)):
        x = get_column_x(0)
        y = vertical_offset + box_idx * (BOX_HEIGHT + VERTICAL_GAP)
        first_positions.append((x, y))
    positions[0] = first_positions

    # Calculate rightmost column - evenly spaced
    last_positions: list[tuple[float, float]] = []
    for box_idx in range(len(last_column)):
        x = get_column_x(len(columns) - 1)
        y = vertical_offset + box_idx * (BOX_HEIGHT + VERTICAL_GAP)
        last_positions.append((x, y))
    positions[-1] = last_positions

    # Process left side (merging towards champion)
    for col_idx in range(1, champion_col_idx + 1):
        column = columns[col_idx]
        prev_column = columns[col_idx - 1]
        prev_positions = positions[col_idx - 1]
        assert prev_positions is not None

        col_positions: list[tuple[float, float]] = []
        x = get_column_x(col_idx)

        for box_idx in range(len(column)):
            # Check if merging (2→1) or same size (1→1)
            if len(prev_column) == len(column):
                # Same size: 1-to-1 mapping
                y = prev_positions[box_idx][1]
            else:
                # Merging: 2-to-1, position at midpoint
                source_idx_1 = box_idx * 2
                source_idx_2 = box_idx * 2 + 1

                if source_idx_2 < len(prev_positions):
                    y1 = prev_positions[source_idx_1][1]
                    y2 = prev_positions[source_idx_2][1]
                    y = (y1 + y2) / 2
                else:
                    y = prev_positions[source_idx_1][1]

            col_positions.append((x, y))

        positions[col_idx] = col_positions

    # Process right side (working backwards from rightmost)
    for col_idx in range(len(columns) - 2, champion_col_idx, -1):
        column = columns[col_idx]
        next_column = columns[col_idx + 1]
        next_positions = positions[col_idx + 1]
        assert next_positions is not None

        col_positions: list[tuple[float, float]] = []
        x = get_column_x(col_idx)

        for box_idx in range(len(column)):
            # Check if same size (1→1) or expanding (1→2)
            if len(column) == len(next_column):
                # Same size: 1-to-1 mapping
                y = next_positions[box_idx][1]
            else:
                # Expanding: 1-to-2, position at midpoint of children
                child_idx_1 = box_idx * 2
                child_idx_2 = box_idx * 2 + 1

                if child_idx_2 < len(next_positions):
                    y1 = next_positions[child_idx_1][1]
                    y2 = next_positions[child_idx_2][1]
                    y = (y1 + y2) / 2
                else:
                    y = next_positions[child_idx_1][1]

            col_positions.append((x, y))

        positions[col_idx] = col_positions

    # Now recenter everything vertically so champion is at a nice position
    # Find champion position
    champion_positions = positions[champion_col_idx]
    assert champion_positions is not None
    if champion_positions:
        champion_y = champion_positions[0][1]

        # Calculate actual bracket extent before centering
        min_y = min(pos[1] for col_positions in positions if col_positions is not None for pos in col_positions)
        max_y_before_shift = max(pos[1] for col_positions in positions if col_positions is not None for pos in col_positions)
        bracket_height = max_y_before_shift - min_y

        # We want the champion at roughly 1/3 from top for visual balance
        # Base this on actual bracket height, not just outer columns
        desired_champion_y = vertical_offset + bracket_height // 3
        y_shift = desired_champion_y - champion_y

        # Apply shift to all positions
        for col_idx in range(len(positions)):
            if positions[col_idx] is not None:
                positions[col_idx] = [(x, y + y_shift) for x, y in positions[col_idx]]

        # After shifting, ensure we don't have negative y values
        # If we do, shift everything down to maintain MARGIN
        min_y_after = min(pos[1] for col_positions in positions if col_positions is not None for pos in col_positions)
        if min_y_after < MARGIN:
            correction = MARGIN - min_y_after
            for col_idx in range(len(positions)):
                if positions[col_idx] is not None:
                    positions[col_idx] = [(x, y + correction) for x, y in positions[col_idx]]

    return positions


def _svg_header(width: float, height: float) -> str:
    """Generate SVG header with styles."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
  <defs>
    <style>
      .box {{ fill: white; stroke: #999; stroke-width: 2; }}
      .box-winner {{ fill: #90EE90; stroke: #28a745; stroke-width: 2; }}
      .box-champion {{ fill: #FFB6C1; stroke: #FF69B4; stroke-width: 3; }}
      .connector {{ stroke: #666; stroke-width: 2; }}
      .text {{ font-family: system-ui, -apple-system, sans-serif; font-size: 12px; fill: black; }}
    </style>
  </defs>
  <rect fill="#f0f0f0" width="{width}" height="{height}"/>
"""


def _draw_box(x: float, y: float, box: Box, is_champion: bool, box_width: float) -> str:
    """Generate SVG for a single box."""
    # Determine CSS class
    if is_champion:
        css_class = "box-champion"
    elif box.is_winner:
        css_class = "box-winner"
    else:
        css_class = "box"

    # Strip emoji from name
    _, name = split_emoji(box.name) if box.name else ("", "")

    # Format text
    if not name:
        text = ""
    elif box.votes is not None:
        text = f"{name} ({box.votes})"
    else:
        text = name

    # Truncate if needed
    if len(text) > MAX_NAME_LENGTH:
        text = text[: MAX_NAME_LENGTH - 3] + "..."

    # Escape XML special characters
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    return f"""  <rect class="{css_class}" x="{x}" y="{y}" width="{box_width}" height="{BOX_HEIGHT}" rx="8"/>
  <text class="text" x="{x + box_width / 2}" y="{y + BOX_HEIGHT / 2 + 4}" text-anchor="middle">{text}</text>
"""


def _draw_bracket_connector(from_x: float, from_y: float, to_x: float, to_y: float, box_width: float) -> str:
    """Draw bracket-style connector (horizontal line with vertical segment if needed)."""
    # From right edge of left box to left edge of right box
    # Vertical center of boxes
    y1 = from_y + BOX_HEIGHT / 2
    y2 = to_y + BOX_HEIGHT / 2
    x1 = from_x + box_width
    x2 = to_x

    if abs(y1 - y2) < 1:
        # Same vertical position - simple horizontal line
        return f"""  <line class="connector" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>
"""
    else:
        # Different vertical positions - draw bracket connector
        # Horizontal line from box, then vertical, then horizontal to next box
        mid_x = (x1 + x2) / 2

        return f"""  <path class="connector" d="M {x1} {y1} H {mid_x} V {y2} H {x2}" fill="none"/>
"""


def _empty_svg() -> str:
    """Generate empty SVG for tournaments with no data."""
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
  <rect fill="#f0f0f0" width="200" height="100"/>
  <text x="100" y="50" text-anchor="middle" font-family="system-ui" font-size="14">No data</text>
</svg>
"""


async def generate_bracket_image(tournament_id: int) -> discord.File:
    """Generate bracket image as Discord file.

    Args:
        tournament_id: Tournament ID to render

    Returns:
        Discord File containing PNG data (converted from SVG)
    """
    # Lazy import to avoid requiring Cairo for tests
    import cairosvg

    # Get tournament state
    tournament = await db.get_state(tournament_id)

    # Generate SVG
    svg_content = render_bracket_svg(tournament)

    # Convert SVG to PNG for Discord compatibility
    png_bytes = cairosvg.svg2png(bytestring=svg_content.encode("utf-8"))

    # Convert to Discord file
    png_io = io.BytesIO(png_bytes)
    return discord.File(png_io, filename="bracket.png")
