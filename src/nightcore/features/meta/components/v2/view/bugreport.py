"""Bug report view v2 component."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

import discord
from discord import Attachment, Color, MediaGalleryItem
from discord.ui import (
    Container,
    LayoutView,
    MediaGallery,
    Separator,
    TextDisplay,
)

from src.nightcore.utils import discord_ts

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class BugReportViewV2(LayoutView):
    def __init__(
        self,
        bot: Nightcore,
        guild_id: int,
        user_id: int,
        long_desc: str,
        screenshot: Attachment | None = None,
    ) -> None:
        super().__init__(timeout=None)

        container = Container[Self](accent_color=Color.from_str("#515cff"))

        container.add_item(
            TextDisplay[Self](
                "## <:3052shinybluebughunter:1442916887213375689> Отчёт об ошибке"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self](
                f"**Пользователь: <@{user_id}> (`{user_id}`)**\n**Сервер: `{guild_id}`**"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self](
                f"### Полное описание проблемы:\n**```{long_desc}```**"
            )
        )
        container.add_item(Separator[Self]())
        if screenshot:
            container.add_item(TextDisplay[Self]("### Вложения:"))
            container.add_item(
                MediaGallery[Self](MediaGalleryItem(screenshot.url))
            )
            container.add_item(Separator[Self]())

        now = discord.utils.utcnow()
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)
