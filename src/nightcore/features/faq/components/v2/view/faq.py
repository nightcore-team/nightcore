"""
FAQ view v2 component.

Used for displaying FAQ information in guilds.
Handles FAQ page button interactions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self, cast

from discord import ButtonStyle, Color, MediaGalleryItem
from discord.interactions import Interaction
from discord.ui import (
    ActionRow,
    Button,
    Container,
    Item,
    LayoutView,
    MediaGallery,
    Separator,
    TextDisplay,
    button,
)

from src.infra.db.models._annot import FAQPageAnnot
from src.nightcore.utils import discord_ts

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class FAQGlobalViewV2(LayoutView):
    def __init__(
        self, bot: Nightcore, text: str | None, image_url: str | None
    ) -> None:
        super().__init__(timeout=None)

        container = Container[Self](accent_color=Color.blurple())

        container.add_item(
            TextDisplay[Self](
                "## <:heartt:1442919985004544011> Часто задаваемые вопросы (FAQ)"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        if text:
            container.add_item(TextDisplay[Self](text))
            container.add_item(Separator[Self]())

        if image_url:
            container.add_item(MediaGallery[Self](MediaGalleryItem(image_url)))
            container.add_item(Separator[Self]())

        container.add_item(
            ActionRow[Self](
                Button[Self](
                    label="Перейти к FAQ",
                    style=ButtonStyle.secondary,
                    emoji="<:heartt:1442919985004544011>",
                    custom_id="faq:open_faq",
                )
            )
        )
        container.add_item(Separator[Self]())

        now = datetime.now(UTC)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}\n"  # type: ignore
            )
        )

        self.add_item(container)


class FAQViewPaginationButtons(ActionRow["FAQViewV2"]):
    def __init__(self):
        super().__init__()

    @button(
        style=ButtonStyle.secondary,
        emoji="<:41036arrowforwardios1:1442925401696632934>",
        custom_id="faq:prev",
    )
    async def previous(
        self,
        interaction: Interaction[Nightcore],
        button: Button[FAQViewV2],
    ):
        """Go to the previous page."""
        view = cast(FAQViewV2, self.view)
        if view.current_page > 0:
            view.current_page -= 1
        await interaction.response.edit_message(
            view=view.make_component(),
        )

    @button(
        style=ButtonStyle.secondary,
        emoji="<:41036arrowforwardios:1442924853085864178>",
        custom_id="faq:next",
    )
    async def next(
        self,
        interaction: Interaction[Nightcore],
        button: Button[FAQViewV2],
    ):
        """Go to the next page."""
        view = cast(FAQViewV2, self.view)
        if view.current_page < len(view.pages) - 1:  # type: ignore
            view.current_page += 1
        await interaction.response.edit_message(
            view=view.make_component(),
        )


class FAQViewV2(LayoutView):
    def __init__(
        self,
        bot: Nightcore,
        pages: list[list[Item[LayoutView]]] | None = None,
        _build: bool = False,
    ) -> None:
        super().__init__(timeout=None)

        self.bot = bot
        self.pages = pages
        self.current_page = 0

        self.actions: FAQViewPaginationButtons | None = None

        if _build:
            self.make_component()

    def _update_buttons(self):
        if not self.actions:
            return
        for child in self.actions.children:
            if isinstance(child, Button):
                if child.custom_id == "faq:prev":
                    child.disabled = self.current_page == 0  # type: ignore
                elif child.custom_id == "faq:next":
                    child.disabled = self.current_page == len(self.pages) - 1  # type: ignore

    def make_component(self) -> Self:
        """Build the FAQ view component."""
        self.clear_items()

        container = Container[Self](accent_color=Color.blurple())

        container.add_item(
            TextDisplay[Self](
                "## <:heartt:1442919985004544011> Часто задаваемые вопросы (FAQ)"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        # sections for each FAQ page
        if self.pages and len(self.pages) > 0:
            match len(self.pages):
                case 1:
                    for item in self.pages[0]:
                        container.add_item(item)
                case _:
                    for item in self.pages[self.current_page]:
                        container.add_item(item)
                    self.actions = FAQViewPaginationButtons()
                    container.add_item(self.actions)
                    container.add_item(Separator[Self]())
        else:
            container.add_item(
                TextDisplay[Self]("В FAQ этого сервера нет страниц.")
            )
            container.add_item(Separator[Self]())

        now = datetime.now(UTC)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}\n"  # type: ignore
            )
        )

        self.add_item(container)
        self._update_buttons()

        return self


class FAQPageViewV2(LayoutView):
    def __init__(self, bot: Nightcore, page: FAQPageAnnot) -> None:
        super().__init__(timeout=None)

        container = Container[Self](accent_color=Color.blurple())

        container.add_item(TextDisplay[Self](f"## {page['title']}"))
        container.add_item(Separator[Self]())

        container.add_item(TextDisplay[Self](f"{page['content']}"))
        container.add_item(Separator[Self]())

        if (
            image_url := page.get("image_url", None)
        ) is not None and image_url:
            media_gallery = MediaGalleryItem(image_url)
            container.add_item(MediaGallery[Self](media_gallery))

        now = datetime.now(UTC)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}\n"  # type: ignore
            )
        )

        self.add_item(container)
