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
        roles_ids: list[int],
        reason: str | None = None,
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
                    "### <:check:1442915033079353404> Запрос на роль одобрен"
                )
                text = f"Модератор <@{moderator_id}> одобрил запрос пользователя <@{user_id}> на роль <@&{roles_ids[0]}>."  # noqa: E501
            case RoleRequestStateEnum.DENIED:
                accent_color = Color.from_str("#F11313")
                header_text = (
                    "### <:failed:1442915170320912506> Запрос на роль отклонен"
                )
                text = f"Модератор <@{moderator_id}> отклонил запрос пользователя <@{user_id}> на роль <@&{roles_ids[0]}> по причине:\n> {self.reason}."  # noqa: E501
            case RoleRequestStateEnum.CANCELED:
                accent_color = Color.from_str("#F11313")
                header_text = (
                    "### <:failed:1442915170320912506> Запрос на роль отменен"
                )
                text = (
                    f"Пользователь <@{user_id}> отменил свой запрос на роль."
                )
            case RoleRequestStateEnum.EXPIRED:
                accent_color = Color.from_str("#F1F113")
                header_text = (
                    "### <:sandclock:1442914884147871874> Запрос на роль истек"
                )
                text = f"Запрос на роль пользователя <@{user_id}> истек."
            case RoleRequestStateEnum.REMOVED:
                accent_color = Color.from_str("#515cff")
                header_text = "### <:remove:1442914236836610119> Роль удалена"
                text = f"Модератор <@{moderator_id}> снял пользователю <@{user_id}> роль(-и) {', '.join(f'<@&{role}>' for role in roles_ids)} по причине:\n> {self.reason}."  # noqa: E501
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
