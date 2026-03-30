"""Rules get view v2 component."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self

from discord import Color
from discord.ui import (
    Container,
    LayoutView,
    Separator,
    TextDisplay,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import discord_ts


class RulesGetViewV2(LayoutView):
    def __init__(self, *, bot: Nightcore, clause: str) -> None:
        super().__init__(timeout=None)

        container = Container[Self](accent_color=Color.from_str("#6559d1"))

        container.add_item(TextDisplay[Self]("## Полученный пункт"))
        container.add_item(Separator[Self]())

        container.add_item(TextDisplay[Self](f"```{clause}```"))

        container.add_item(
            TextDisplay[Self](
                "-# если введенный пункт отсутствует, вы увидите свой ввод"
            )
        )

        container.add_item(Separator[Self]())

        now = datetime.now(UTC)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )
