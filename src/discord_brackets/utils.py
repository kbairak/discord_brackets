import functools
import re

import discord
import emoji

from . import types


def create_match_poll(match: types.Match) -> discord.Poll:
    """Create a poll for a match, extracting emojis from option names."""
    # Extract emojis and text from both options
    left_emoji, left_text = split_emoji(match.left.name)
    right_emoji, right_text = split_emoji(match.right.name)

    # Use custom emoji if present, otherwise default
    left_poll_emoji = left_emoji or "1️⃣"
    right_poll_emoji = right_emoji or "2️⃣"

    # If both are the same, use defaults
    if left_poll_emoji == right_poll_emoji:
        left_poll_emoji = "1️⃣"
        right_poll_emoji = "2️⃣"

    # Question shows full names with shortcodes converted to Unicode emojis
    # (Discord will render Unicode emojis but not shortcodes in poll questions)
    def convert_shortcodes(text: str) -> str:
        """Convert Discord shortcodes to Unicode emojis in text."""

        def replace_shortcode(match):
            shortcode = match.group()
            try:
                partial_emoji = discord.PartialEmoji.from_str(shortcode)
                if partial_emoji.is_unicode_emoji():
                    return str(partial_emoji)
            except Exception:
                pass
            return shortcode

        return re.sub(r":([\w]+):", replace_shortcode, text)

    left_display = convert_shortcodes(match.left.name)
    right_display = convert_shortcodes(match.right.name)
    question = f"{left_display} vs {right_display}"

    return discord.Poll(
        question=question,
        answers=[
            discord.PollAnswer(text=left_text, emoji=left_poll_emoji),
            discord.PollAnswer(text=right_text, emoji=right_poll_emoji),
        ],
        duration=24 * 30,
    )


def split_emoji(text: str) -> tuple[str, str]:
    """Split emoji from the start of text.

    >>> split_emoji("😄 hello world")
    ("😄", "hello world")
    >>> split_emoji("<:custom:123> hello")
    ("<:custom:123>", "hello")
    >>> split_emoji(":fire: hello")
    ("🔥", "hello")
    >>> split_emoji("no emoji here")
    ("", "no emoji here")
    """
    text = text.strip()
    if not text:
        return ("", "")

    # Check for custom Discord emoji <:name:id> or <a:name:id> (animated)
    custom_match = re.match(r"^<a?:\w+:\d+>", text)
    if custom_match:
        emoji_str = custom_match.group()
        rest = text[len(emoji_str) :].strip()
        return (emoji_str, rest)

    # Check for Discord shortcode :name: (including underscores)
    shortcode_match = re.match(r"^:([\w]+):", text)
    if shortcode_match:
        shortcode = shortcode_match.group()
        rest = text[len(shortcode) :].strip()

        # Try to convert shortcode to Unicode emoji using py-cord
        try:
            partial_emoji = discord.PartialEmoji.from_str(shortcode)
            if partial_emoji.is_unicode_emoji():
                return (str(partial_emoji), rest)
            else:
                # Custom guild emoji without ID, can't use it
                return ("", rest)
        except Exception:
            # Shortcode didn't convert, strip it and use default
            return ("", rest)

    # Check for Unicode emoji at start using emoji library
    # Extract emojis from text
    emojis = emoji.emoji_list(text)
    if emojis and emojis[0]["match_start"] == 0:
        # First emoji is at the start
        first_emoji = emojis[0]
        emoji_str = text[first_emoji["match_start"] : first_emoji["match_end"]]
        rest = text[first_emoji["match_end"] :].strip()
        return (emoji_str, rest)

    return ("", text)


@functools.cache
def get_recursive_seed_ordering(size: int) -> list[int]:
    """Usage:

    >>> get_recursive_seed_ordering(1)
    <<< [0]

    >>> get_recursive_seed_ordering(2)
    <<< [0, 1]

    >>> get_recursive_seed_ordering(4)
    <<< [0, 3, 1, 2]

    >>> get_recursive_seed_ordering(8)
    <<< [0, 7, 3, 4, 1, 6, 2, 5]
    """

    assert size == 1 or (size > 1 and size.bit_count() == 1), "Only powers of 2 are supported"

    if size == 1:
        return [0]
    result = []
    for i in get_recursive_seed_ordering(size // 2):
        result.append(i)
        # i + x = size - 1 => x = size - i - 1
        result.append(size - i - 1)
    return result


def get_recursive_seed_index(x: int, size: int):
    ordering = get_recursive_seed_ordering(size)
    return ordering.index(x)
