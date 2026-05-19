"""Inactive request view."""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self

import discord
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
    from src.infra.db.models._enums import InactiveRequestStateEnum
    from src.nightcore.bot import Nightcore


from src.nightcore.utils import discord_ts

logger = logging.getLogger(__name__)


class InactiveRequestViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        author_id: int,
        message: str,
        state: "InactiveRequestStateEnum",
        ping_role_id: int | None = None,
        user_answer_id: int | None = None,
        answer: str | None = None,
    ):
        super().__init__(timeout=None)

        accent_color = None
        if state == InactiveRequestStateEnum.APPROVED:
            accent_color = discord.Color.green()
        elif state == InactiveRequestStateEnum.DENIED:
            accent_color = discord.Color.red()

        status = "На рассмотрении"
        if state == InactiveRequestStateEnum.APPROVED:
            status = "Одобрено"
        elif state == InactiveRequestStateEnum.DENIED:
            status = "Отклонено"

        container = Container[Self](accent_color=accent_color)

        container.add_item(TextDisplay("## Заявление на неактив"))
        container.add_item(TextDisplay(f"> Автор: <@{author_id}>"))
        container.add_item(Separator())

        container.add_item(TextDisplay(f"```{message}```"))
        container.add_item(Separator())
        container.add_item(
            ActionRow[Self](
                Button(
                    style=ButtonStyle.green,
                    emoji="<:check:1442915033079353404>",
                    label="Одобрить",
                    custom_id=f"inactive:{author_id}:approve",
                    disabled=state
                    in [
                        InactiveRequestStateEnum.APPROVED,
                        InactiveRequestStateEnum.DENIED,
                    ],
                ),
                Button(
                    style=ButtonStyle.red,
                    emoji="<:failed:1442915170320912506>",
                    label="Отклонить",
                    custom_id=f"inactive:{author_id}:deny",
                    disabled=state
                    in [
                        InactiveRequestStateEnum.APPROVED,
                        InactiveRequestStateEnum.DENIED,
                    ],
                ),
            )
        )
        container.add_item(Separator())

        now = datetime.now(UTC)
        footer_text = f"-# Статус: {status}"
        if ping_role_id:
            footer_text = f"{footer_text} | <@&{ping_role_id}>"

        container.add_item(TextDisplay(footer_text))
        if user_answer_id and answer:
            container.add_item(
                TextDisplay(
                    f"### Решение от <@{user_answer_id}> ({discord_ts(now)}):\n```{answer}```"  # noqa: E501
                )
            )

        container.add_item(TextDisplay(footer_text))

        self.add_item(container)
