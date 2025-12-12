"""Winter holidays view v2 component."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self

from discord import Color, MediaGalleryItem
from discord.ui import (
    Container,
    LayoutView,
    MediaGallery,
    Separator,
    TextDisplay,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import discord_ts


class WinterHolidaysViewV2(LayoutView):
    def __init__(
        self,
        bot: Nightcore,
        calendar: str,
        tz: str,
        holidays: list[dict[str, object]],
        image_url: str | None,
    ) -> None:
        super().__init__()

        container = Container[Self](accent_color=Color.from_str("#bc9af4"))

        container.add_item(
            TextDisplay[Self](
                "## <:celebration:1449138486585200732> Зимние праздники\n"
            )
        )
        container.add_item(
            TextDisplay[Self](
                "> Календарь: **"
                + calendar.capitalize()
                + "**\n> Часовой пояс: **"
                + tz
                + "**\n"
            )
        )
        container.add_item(Separator[Self]())

        for holiday in holidays:
            container.add_item(
                TextDisplay[Self](
                    f"**{holiday['name']}**\n> **{holiday['month']}** — осталось **{holiday['days']}** дней **{holiday['hours']}** часов **{holiday['minutes']}** минут **{holiday['seconds']}** секунд\n"  # noqa: E501
                )
            )

        container.add_item(Separator[Self]())

        if image_url:
            container.add_item(MediaGallery[Self](MediaGalleryItem(image_url)))
            container.add_item(Separator[Self]())

        now = datetime.now(timezone.utc)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)
