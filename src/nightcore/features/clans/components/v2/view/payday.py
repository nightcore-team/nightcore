"""Clans Payday View V2 Component."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self

from discord.ui import Container, LayoutView, Separator, TextDisplay

from src.nightcore.utils import discord_ts

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class ClansPaydayViewV2(LayoutView):
    def __init__(self, bot: "Nightcore") -> None:
        super().__init__(timeout=None)

        container = Container[Self]()

        container.add_item(
            TextDisplay[Self]("## <:241508crown:1442923559541407844> PayDay")
        )
        container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self](
                "Всем кланам были выданы очки репутации в зависимости от количества участников и множителя PayDay."  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        now = datetime.now(timezone.utc)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)
