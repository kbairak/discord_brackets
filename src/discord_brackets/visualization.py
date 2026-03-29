import io

import discord
from PIL import Image, ImageDraw, ImageFont

from . import db, types, utils


def draw_rounded_rectangle(draw, xy, radius=10, fill=None, outline=None, width=1):
    """Draw a rounded rectangle."""
    x1, y1, x2, y2 = xy
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill, outline=outline, width=0)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill, outline=outline, width=0)
    draw.pieslice(
        [x1, y1, x1 + radius * 2, y1 + radius * 2], 180, 270, fill=fill, outline=outline, width=0
    )
    draw.pieslice(
        [x2 - radius * 2, y1, x2, y1 + radius * 2], 270, 360, fill=fill, outline=outline, width=0
    )
    draw.pieslice(
        [x1, y2 - radius * 2, x1 + radius * 2, y2], 90, 180, fill=fill, outline=outline, width=0
    )
    draw.pieslice(
        [x2 - radius * 2, y2 - radius * 2, x2, y2], 0, 90, fill=fill, outline=outline, width=0
    )
    if outline:
        draw.arc([x1, y1, x1 + radius * 2, y1 + radius * 2], 180, 270, fill=outline, width=width)
        draw.arc([x2 - radius * 2, y1, x2, y1 + radius * 2], 270, 360, fill=outline, width=width)
        draw.arc([x1, y2 - radius * 2, x1 + radius * 2, y2], 90, 180, fill=outline, width=width)
        draw.arc([x2 - radius * 2, y2 - radius * 2, x2, y2], 0, 90, fill=outline, width=width)
        draw.line([x1 + radius, y1, x2 - radius, y1], fill=outline, width=width)
        draw.line([x1 + radius, y2, x2 - radius, y2], fill=outline, width=width)
        draw.line([x1, y1 + radius, x1, y2 - radius], fill=outline, width=width)
        draw.line([x2, y1 + radius, x2, y2 - radius], fill=outline, width=width)


async def generate_bracket_image(tournament_id: int) -> discord.File:
    """Generate a visual bracket representation."""
    # Get tournament state
    state = await db.get_state(tournament_id)

    # Define layout constants
    box_height = 35
    vertical_gap = 15
    margin = 50

    # Calculate box width based on longest option name (without emojis)
    max_name_length = 0
    for round_obj in state.rounds:
        for match in round_obj.matches:
            _, left_text = utils.split_emoji(match.left.name)
            _, right_text = utils.split_emoji(match.right.name)
            max_name_length = max(max_name_length, len(left_text), len(right_text))

    # Add space for vote count " (999)" and some padding
    box_width = max(120, max_name_length * 8 + 50)
    x_spacing = box_width + 60

    # Calculate positions for each round
    round_positions = []
    for round_idx, round_obj in enumerate(state.rounds):
        positions = []

        # Play-in round vs regular rounds spacing
        if round_idx == 0 and round_obj.name == "Play-in round":
            spacing = int((box_height * 2 + vertical_gap) * 1.5)
        else:
            spacing = (box_height * 2 + vertical_gap) * (2**round_idx)

        for match_idx, match in enumerate(round_obj.matches):
            y_pos = margin + match_idx * spacing
            positions.append({"match": match, "y": y_pos})

        round_positions.append(positions)

    # Check if tournament is finished
    final_match = state.rounds[-1].matches[0] if state.rounds else None
    tournament_finished = final_match and (final_match.left.winner or final_match.right.winner)

    # Calculate image dimensions
    num_rounds = len(state.rounds)
    max_height = max(
        pos[-1]["y"] + box_height * 2 + vertical_gap + margin
        for pos in round_positions
        if pos
    )

    # Add space for winner box if tournament finished
    width = margin * 2 + num_rounds * x_spacing + box_width
    if tournament_finished:
        width += 200

    height = max(600, max_height)

    # Create image
    img = Image.new("RGB", (width, height), color="#f0f0f0")
    draw = ImageDraw.Draw(img)

    # Load font with fallback
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 11)
    except Exception:
        font = ImageFont.load_default()

    # Draw each round
    for round_idx, positions in enumerate(round_positions):
        x = margin + round_idx * x_spacing

        for match_pos in positions:
            match = match_pos["match"]
            y = match_pos["y"]

            # Draw left option box
            _draw_option_box(
                draw, font, x, y, box_width, box_height, match.left.name, match.left.votes, match.left.winner
            )

            # Draw right option box
            y2 = y + box_height + vertical_gap
            _draw_option_box(
                draw,
                font,
                x,
                y2,
                box_width,
                box_height,
                match.right.name,
                match.right.votes,
                match.right.winner,
            )

            # Draw connecting lines FROM previous round
            if round_idx > 0:
                # Draw line to left option from its previous match
                if match.left.advanced_from is not None:
                    prev_match_y = round_positions[round_idx - 1][match.left.advanced_from]["y"]
                    _draw_incoming_line(
                        draw, x, y, box_width, box_height, vertical_gap, x_spacing, prev_match_y
                    )

                # Draw line to right option from its previous match
                if match.right.advanced_from is not None:
                    prev_match_y = round_positions[round_idx - 1][match.right.advanced_from]["y"]
                    _draw_incoming_line(
                        draw,
                        x,
                        y + box_height + vertical_gap,
                        box_width,
                        box_height,
                        vertical_gap,
                        x_spacing,
                        prev_match_y,
                    )

    # Draw winner box if tournament finished
    if tournament_finished:
        winner_name = final_match.left.name if final_match.left.winner else final_match.right.name
        # Strip emojis from winner name
        _, display_winner = utils.split_emoji(winner_name)

        winner_x = width - margin - 150
        winner_y = height // 2 - 30

        # Draw golden winner box
        draw_rounded_rectangle(
            draw,
            [winner_x, winner_y, winner_x + 140, winner_y + 60],
            radius=15,
            fill="#FFD700",
            outline="#FFA500",
            width=3,
        )

        # Draw winner name in larger font
        try:
            winner_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
        except Exception:
            winner_font = font

        # Truncate if too long
        if len(display_winner) > 14:
            display_winner = display_winner[:12] + "..."

        # Center text
        text_bbox = draw.textbbox((0, 0), display_winner, font=winner_font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        text_x = winner_x + (140 - text_width) // 2
        text_y = winner_y + (60 - text_height) // 2

        draw.text((text_x, text_y), display_winner, fill="#000", font=winner_font)

        # Draw line from final match to winner
        final_x = margin + (num_rounds - 1) * x_spacing + box_width
        final_y = round_positions[-1][0]["y"] + box_height + vertical_gap // 2

        draw.line([final_x, final_y, final_x + 30, final_y], fill="#666", width=2)
        draw.line([final_x + 30, final_y, final_x + 30, winner_y + 30], fill="#666", width=2)
        draw.line([final_x + 30, winner_y + 30, winner_x, winner_y + 30], fill="#666", width=2)

    # Convert to Discord file
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    return discord.File(img_bytes, filename="bracket.png")


def _draw_option_box(draw, font, x, y, box_width, box_height, name, votes, is_winner):
    """Draw a single option box with name and vote count."""
    # Strip emojis from name (PIL can't render custom guild emojis)
    _, display_name = utils.split_emoji(name)

    # Include vote count if available
    if votes is not None:
        display_text = f"{display_name} ({votes})"
    else:
        display_text = display_name

    # Truncate if text is too wide for the box (with some padding)
    max_width = box_width - 10  # 5px padding on each side
    text_bbox = draw.textbbox((0, 0), display_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]

    if text_width > max_width:
        # Truncate and add ellipsis
        while text_width > max_width and len(display_text) > 4:
            display_text = display_text[:-4] + "..."
            text_bbox = draw.textbbox((0, 0), display_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]

    # Colors based on winner status
    box_color = "#90EE90" if is_winner else "white"
    outline_color = "#28a745" if is_winner else "#999"

    # Draw rounded rectangle
    draw_rounded_rectangle(
        draw, [x, y, x + box_width, y + box_height], radius=8, fill=box_color, outline=outline_color, width=2
    )

    # Center text in box
    text_bbox = draw.textbbox((0, 0), display_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_x = x + (box_width - text_width) // 2
    text_y = y + (box_height - text_height) // 2

    draw.text((text_x, text_y), display_text, fill="black", font=font)


def _draw_incoming_line(draw, current_x, current_y, box_width, box_height, vertical_gap, x_spacing, prev_match_y):
    """Draw line from previous round match to current option box."""
    # Target point (middle of current option box)
    target_x = current_x
    target_y = current_y + box_height // 2

    # Source point (center of previous match, between its two boxes)
    prev_x = current_x - x_spacing + box_width
    source_y = prev_match_y + box_height + vertical_gap // 2

    # Draw L-shaped line from previous match to current box
    mid_x = prev_x + 30

    # Horizontal from previous match
    draw.line([prev_x, source_y, mid_x, source_y], fill="#666", width=2)

    # Vertical
    draw.line([mid_x, source_y, mid_x, target_y], fill="#666", width=2)

    # Horizontal to current box
    draw.line([mid_x, target_y, target_x, target_y], fill="#666", width=2)
