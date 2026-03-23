from __future__ import annotations

import io
from PIL import Image, ImageDraw, ImageFont
import discord
from database import models


def draw_rounded_rectangle(draw, xy, radius=10, fill=None, outline=None, width=1):
    """Draw a rounded rectangle."""
    x1, y1, x2, y2 = xy
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill, outline=outline, width=0)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill, outline=outline, width=0)
    draw.pieslice([x1, y1, x1 + radius * 2, y1 + radius * 2], 180, 270, fill=fill, outline=outline, width=0)
    draw.pieslice([x2 - radius * 2, y1, x2, y1 + radius * 2], 270, 360, fill=fill, outline=outline, width=0)
    draw.pieslice([x1, y2 - radius * 2, x1 + radius * 2, y2], 90, 180, fill=fill, outline=outline, width=0)
    draw.pieslice([x2 - radius * 2, y2 - radius * 2, x2, y2], 0, 90, fill=fill, outline=outline, width=0)
    if outline:
        draw.arc([x1, y1, x1 + radius * 2, y1 + radius * 2], 180, 270, fill=outline, width=width)
        draw.arc([x2 - radius * 2, y1, x2, y1 + radius * 2], 270, 360, fill=outline, width=width)
        draw.arc([x1, y2 - radius * 2, x1 + radius * 2, y2], 90, 180, fill=outline, width=width)
        draw.arc([x2 - radius * 2, y2 - radius * 2, x2, y2], 0, 90, fill=outline, width=width)
        draw.line([x1 + radius, y1, x2 - radius, y1], fill=outline, width=width)
        draw.line([x1 + radius, y2, x2 - radius, y2], fill=outline, width=width)
        draw.line([x1, y1 + radius, x1, y2 - radius], fill=outline, width=width)
        draw.line([x2, y1 + radius, x2, y2 - radius], fill=outline, width=width)


async def generate_bracket_image(bracket_id: int) -> discord.File:
    """
    Generate a visual representation of the bracket in horizontal tournament style.
    """
    bracket = await models.get_bracket(bracket_id)
    if bracket is None:
        raise ValueError(f"Bracket {bracket_id} not found")

    contestants_dict = {}

    # Get all contestants
    all_contestants = await models.get_contestants(bracket_id, include_eliminated=True)
    for c in all_contestants:
        contestants_dict[c["id"]] = c

    # Get all rounds
    current_round = bracket["current_round"]
    all_rounds = []

    # Start from round 0 (play-ins) or round 1
    start_round = 0
    for round_num in range(0, current_round + 1):
        round_matches = await models.get_round_matches(bracket_id, round_num)
        if round_matches:
            all_rounds.append((round_num, round_matches))
            if start_round == 0 and round_num > 0:
                start_round = round_num

    if not all_rounds:
        # No matches yet, create a simple placeholder image
        img = Image.new("RGB", (800, 200), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((400, 100), "Bracket not started yet", fill="black", anchor="mm")
    else:
        # Build the bracket structure - track positions of each match
        box_width = 120
        box_height = 35
        x_spacing = 180
        vertical_gap = 15
        margin = 50

        # Calculate positions for each round
        round_positions = []

        for round_idx, (round_num, matches) in enumerate(all_rounds):
            positions = []

            if round_idx == 0 and len(all_rounds) > 1:
                # Play-in round - use slightly increased spacing
                # Matches are already in the correct order from bracket generation
                play_in_spacing = int((box_height * 2 + vertical_gap) * 1.5)

                for match_idx, match in enumerate(matches):
                    y_pos = margin + match_idx * play_in_spacing
                    positions.append({
                        "match": match,
                        "y": y_pos,
                        "c1_id": match["contestant_1_id"],
                        "c2_id": match["contestant_2_id"],
                        "winner_id": match["winner_id"]
                    })
            else:
                # Regular rounds - standard exponential spacing
                spacing_multiplier = 2 ** round_idx

                for match_idx, match in enumerate(matches):
                    y_pos = margin + match_idx * (box_height * 2 + vertical_gap) * spacing_multiplier
                    positions.append({
                        "match": match,
                        "y": y_pos,
                        "c1_id": match["contestant_1_id"],
                        "c2_id": match["contestant_2_id"],
                        "winner_id": match["winner_id"]
                    })

            round_positions.append(positions)

        # Calculate image dimensions
        num_rounds = len(all_rounds)
        max_height = max(pos[-1]["y"] + box_height * 2 + vertical_gap + margin
                        for pos in round_positions if pos)

        width = margin * 2 + num_rounds * x_spacing + box_width
        height = max(600, max_height)

        # Add space for winner box if completed
        if bracket["phase"] == "completed":
            width += 200

        img = Image.new("RGB", (width, height), color="#f0f0f0")
        draw = ImageDraw.Draw(img)

        # Try to load a font
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
                c1_id = match_pos["c1_id"]
                c2_id = match_pos["c2_id"]
                winner_id = match_pos["winner_id"]

                # Get vote counts for this match
                vote_counts = await models.get_vote_counts(match["id"])

                # Draw contestant 1 box
                if c1_id:
                    c1_name = contestants_dict[c1_id]["name"]
                    c1_votes = vote_counts.get(c1_id, 0)

                    # Format: "name (votes)"
                    display_name = c1_name
                    if len(display_name) > 9:
                        display_name = display_name[:7] + "..."
                    display_text = f"{display_name} ({c1_votes})"

                    is_winner = winner_id == c1_id
                    box_color = "#90EE90" if is_winner else "white"
                    outline_color = "#28a745" if is_winner else "#999"

                    draw_rounded_rectangle(
                        draw,
                        [x, y, x + box_width, y + box_height],
                        radius=8,
                        fill=box_color,
                        outline=outline_color,
                        width=2
                    )

                    text_bbox = draw.textbbox((0, 0), display_text, font=font)
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                    text_x = x + (box_width - text_width) // 2
                    text_y = y + (box_height - text_height) // 2

                    draw.text((text_x, text_y), display_text, fill="black", font=font)

                # Draw contestant 2 box
                if c2_id:
                    c2_name = contestants_dict[c2_id]["name"]
                    c2_votes = vote_counts.get(c2_id, 0)

                    # Format: "name (votes)"
                    display_name = c2_name
                    if len(display_name) > 9:
                        display_name = display_name[:7] + "..."
                    display_text = f"{display_name} ({c2_votes})"

                    is_winner = winner_id == c2_id
                    box_color = "#90EE90" if is_winner else "white"
                    outline_color = "#28a745" if is_winner else "#999"

                    y2 = y + box_height + vertical_gap

                    draw_rounded_rectangle(
                        draw,
                        [x, y2, x + box_width, y2 + box_height],
                        radius=8,
                        fill=box_color,
                        outline=outline_color,
                        width=2
                    )

                    text_bbox = draw.textbbox((0, 0), display_text, font=font)
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                    text_x = x + (box_width - text_width) // 2
                    text_y = y2 + (box_height - text_height) // 2

                    draw.text((text_x, text_y), display_text, fill="black", font=font)

                # Draw connecting lines to next round
                if round_idx < num_rounds - 1 and winner_id:
                    # Find this winner in the next round
                    next_round_positions = round_positions[round_idx + 1]
                    next_x = margin + (round_idx + 1) * x_spacing

                    for next_match_pos in next_round_positions:
                        if winner_id in [next_match_pos["c1_id"], next_match_pos["c2_id"]]:
                            # Determine which box the winner goes to
                            if next_match_pos["c1_id"] == winner_id:
                                next_y = next_match_pos["y"] + box_height // 2
                            else:
                                next_y = next_match_pos["y"] + box_height + vertical_gap + box_height // 2

                            # Draw connection from match center to next box
                            match_center_y = y + box_height + vertical_gap // 2

                            # Horizontal line from match
                            line_x1 = x + box_width
                            line_x2 = x + box_width + 30
                            draw.line([line_x1, match_center_y, line_x2, match_center_y],
                                     fill="#666", width=2)

                            # Vertical line
                            draw.line([line_x2, match_center_y, line_x2, next_y],
                                     fill="#666", width=2)

                            # Horizontal line to next box
                            draw.line([line_x2, next_y, next_x, next_y],
                                     fill="#666", width=2)
                            break

        # Draw winner box if bracket is completed
        if bracket["phase"] == "completed":
            winner_contestant = None
            for c in all_contestants:
                if c["eliminated_in_round"] is None:
                    winner_contestant = c
                    break

            if winner_contestant:
                winner_x = width - margin - 150
                winner_y = height // 2 - 30

                draw_rounded_rectangle(
                    draw,
                    [winner_x, winner_y, winner_x + 140, winner_y + 60],
                    radius=15,
                    fill="#FFD700",
                    outline="#FFA500",
                    width=3
                )

                name = winner_contestant["name"]
                if len(name) > 14:
                    name = name[:12] + "..."

                text_bbox = draw.textbbox((0, 0), name, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                text_x = winner_x + (140 - text_width) // 2
                text_y = winner_y + (60 - text_height) // 2

                draw.text((text_x, text_y), name, fill="#000", font=font)

                # Draw line from last round to winner
                if round_positions:
                    last_round_pos = round_positions[-1][0]
                    last_x = margin + (num_rounds - 1) * x_spacing + box_width
                    last_y = last_round_pos["y"] + box_height + vertical_gap // 2

                    draw.line([last_x, last_y, last_x + 30, last_y], fill="#666", width=2)
                    draw.line([last_x + 30, last_y, last_x + 30, winner_y + 30], fill="#666", width=2)
                    draw.line([last_x + 30, winner_y + 30, winner_x, winner_y + 30], fill="#666", width=2)

    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    return discord.File(img_bytes, filename="bracket.png")
