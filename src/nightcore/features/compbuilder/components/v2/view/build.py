"""Build view v2 component."""

from __future__ import annotations

from typing import Self

from discord import Attachment, Color, MediaGalleryItem
from discord.ui import (
    Container,
    LayoutView,
    MediaGallery,
    Separator,
    TextDisplay,
)


class CustomView(LayoutView):
    def __init__(
        self,
        name: str,
        text: str,
        color: Color | None = None,
        author_text: str | None = None,
        image: str | Attachment | None = None,
    ) -> None:
        super().__init__(timeout=30)

        container = Container[Self](accent_color=color)

        container.add_item(TextDisplay[Self](f"## {name}"))
        container.add_item(Separator[Self]())

        container.add_item(TextDisplay[Self](text))
        container.add_item(Separator[Self]())

        if image:
            if isinstance(image, str):
                media_item = MediaGalleryItem(media=image)
            else:
                media_item = MediaGalleryItem(media=image.url)

            container.add_item(MediaGallery[Self](media_item))
            container.add_item(Separator[Self]())

        if author_text:
            container.add_item(TextDisplay[Self](f"-# {author_text}"))

        self.add_item(container)


def build_view(
    name: str,
    text: str,
    color: Color | None = None,
    author_text: str | None = None,
    image: str | Attachment | None = None,
) -> CustomView:
    """Build view component."""

    return CustomView(
        name=name,
        text=text,
        color=color,
        author_text=author_text,
        image=image,
    )
