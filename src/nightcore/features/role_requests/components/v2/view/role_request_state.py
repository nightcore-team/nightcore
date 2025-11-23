"""Role request state view."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self

from discord import ButtonStyle, Color
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

from src.infra.db.models._enums import RoleRequestStateEnum
from src.nightcore.utils import discord_ts


class LinksActionRow(ActionRow["RoleRequestStateView"]):
    def __init__(self, message_url: str, image_url: str, image_proxy_url: str):
        super().__init__()
        self.add_item(
            Button(style=ButtonStyle.link, label="Сообщение", url=message_url)
        )
        self.add_item(
            Button(style=ButtonStyle.link, label="Image URL", url=image_url)
        )
        self.add_item(
            Button(
                style=ButtonStyle.link,
                label="Image URL (Proxy)",
                url=image_proxy_url,
            )
        )


class RoleRequestStateView(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        moderator_id: int,
        user_id: int,
        state: RoleRequestStateEnum,
        role_id: int | None = None,
        reason: str | None = None,
        message_url: str | None = None,
        image_url: str | None = None,
        image_proxy_url: str | None = None,
    ):
        super().__init__()

        self.reason = reason

        header_text = ""
        text = ""
        accent_color: Color | None = None

        match state:
            case RoleRequestStateEnum.APPROVED:
                accent_color = Color.from_str("#32F113")
                header_text = (
                    "### <:check:1442198763694329959> Запрос на роль одобрен"
                )
                text = f"Модератор <@{moderator_id}> одобрил запрос пользователя <@{user_id}> на роль <@&{role_id}>."  # noqa: E501
            case RoleRequestStateEnum.DENIED:
                accent_color = Color.from_str("#F11313")
                header_text = (
                    "### <:failed:1442197027822768270> Запрос на роль отклонен"
                )
                text = f"Модератор <@{moderator_id}> отклонил запрос пользователя <@{user_id}> на роль <@&{role_id}> по причине:\n> {self.reason}."  # noqa: E501
            case RoleRequestStateEnum.CANCELED:
                accent_color = Color.from_str("#F11313")
                header_text = (
                    "### <:failed:1442197027822768270> Запрос на роль отменен"
                )
                text = (
                    f"Пользователь <@{user_id}> отменил свой запрос на роль."
                )
            case RoleRequestStateEnum.EXPIRED:
                accent_color = Color.from_str("#F1F113")
                header_text = (
                    "### <:sandclock:1442203739736768632> Запрос на роль истек"
                )
                text = f"Запрос на роль пользователя <@{user_id}> истек."
            case _:
                ...

        container = Container[Self](accent_color=accent_color)

        container.add_item(TextDisplay(header_text))
        container.add_item(Separator())
        container.add_item(TextDisplay(text))
        container.add_item(Separator())

        now = datetime.now(timezone.utc)

        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}\n"  # type: ignore
            )
        )

        self.add_item(container)
