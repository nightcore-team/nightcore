"""Build embed component."""

from __future__ import annotations

from discord import Attachment, Color, Embed


def build_embed(
    name: str,
    text: str,
    color: Color | None = None,
    author_text: str | None = None,
    image: str | Attachment | None = None,
) -> Embed:
    """Build an embed component."""
    embed = Embed(
        title=name,
        description=text,
        color=color,
    )

    if author_text:
        embed.set_footer(text=author_text)

    if image:
        if isinstance(image, Attachment):
            embed.set_image(url=image.url)
        else:
            embed.set_image(url=image)

    return embed
