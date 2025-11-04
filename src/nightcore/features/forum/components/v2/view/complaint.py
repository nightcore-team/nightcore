"""
Complaint view v2 component.

Used for displaying complaint information in forum threads.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self

from discord import ButtonStyle
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    Separator,
    TextDisplay,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import discord_ts


class ComplaintActionRow(ActionRow["ComplaintViewV2"]):
    def __init__(self, url: str) -> None:
        super().__init__()

        self.url = url

        self.add_item(
            Button["ComplaintViewV2"](
                style=ButtonStyle.link,
                label="Ссылка на жалобу",
                url=self.url,
                emoji="<:7926copymessagelink:1428766635019206838>",
            )
        )


class ComplaintViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        url: str,
        moderator_id: int,
        ping_role_id: int,
        reason: str,
    ) -> None:
        super().__init__(timeout=None)

        container = Container[Self]()

        container.add_item(
            TextDisplay[Self](
                f"### <:91897shield:1428790354781405304> | Жалоба <:42920arrowrightalt:1421170550759489616> <@&{ping_role_id}>"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self](
                "На форуме создана новая жалоба на модератора сервера.\n"
                "Тема успешно была закреплена и ей был установлен префикс."
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self](
                "### Информация о жалобе\n"
                f"Модератор: <@{moderator_id}>\n"
                f"ID модератора: {moderator_id}\n"
                f"Причина: {reason}\n"
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(ComplaintActionRow(url))
        container.add_item(Separator[Self]())

        now = datetime.now(timezone.utc)

        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}\n"  # type: ignore
            )
        )

        self.add_item(container)
