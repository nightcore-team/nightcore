"""Utilities related to content."""

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from discord.partial_emoji import PartialEmoji

CUSTOM_EMOJI_RE = re.compile(r"<?(?:a)?:([A-Za-z0-9_]+):([0-9]{13,20})>?")


def parse_emoji(value: str | None) -> "PartialEmoji | None":
    """Parse an emoji string into a PartialEmoji.

    Accepts custom emoji markup (``<:name:id>``, ``<a:name:id>``) and unicode
    emoji. Anything else - including empty strings, plain names and words -
    would be sent to Discord as a unicode emoji name and rejected with
    ``Invalid Form Body``, so ``None`` is returned instead.
    """

    if value is None:
        return None

    value = value.strip()
    if not value:
        return None

    from discord import PartialEmoji

    if CUSTOM_EMOJI_RE.fullmatch(value):
        return PartialEmoji.from_str(value)

    if any(ord(char) > 0x2000 for char in value):
        return PartialEmoji.from_str(value)

    return None


def has_url_in_content(content: str) -> bool:
    """Check if the content contains a URL."""
    url_pattern = re.compile(
        r"(https?://[^\s]+)|(www\.[^\s]+)",
        re.IGNORECASE,
    )
    return bool(url_pattern.search(content))


def is_image_url(url: str | None) -> bool:
    """Check if the URL points to an image based on file extension."""
    image_extensions = (
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".svg",
        ".webp",
        ".ico",
        ".tiff",
        ".tif",
    )

    if url is None:
        return False

    url_without_params = url.split("?")[0].split("#")[0]
    return url_without_params.lower().endswith(image_extensions)
