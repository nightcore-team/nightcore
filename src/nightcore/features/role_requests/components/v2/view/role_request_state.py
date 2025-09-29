"""Role request state view."""

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
        container = Container[Self]()

        _is_stats: bool = False
        text = ""
        match state:
            case RoleRequestStateEnum.STATS_PROVIDED:
                _is_stats = True
                header_text = f"### <:72151staff:1421169506230866050> | STATS <:42920arrowrightalt:1421170550759489616> <@{moderator_id}>"  # noqa: E501
                text = f"Пользователь <@{user_id}> предоставил вам запрошенную статистику."  # noqa: E501
            case RoleRequestStateEnum.REQUESTED:
                header_text = f"### <:72151staff:1421169506230866050> | REQUESTED <:42920arrowrightalt:1421170550759489616> <@{moderator_id}>"  # noqa: E501
                text = f"Вы запросили статистику у пользователя <@{user_id}>."  # noqa: RUF001
            case RoleRequestStateEnum.APPROVED:
                header_text = f"### <:52104checkmark:1414732973005340672> | APPROVED <:42920arrowrightalt:1421170550759489616> <@{moderator_id}>"  # noqa: E501
                text = f"Вы успешно одобрили пользователю <@{user_id}> роль <@&{role_id}>."  # noqa: E501
            case RoleRequestStateEnum.DENIED:
                header_text = f"### <:9349_nope:1414732960841859182> | DENIED <:42920arrowrightalt:1421170550759489616> <@{moderator_id}>"  # noqa: E501
                text = f"Вы отклонили запрос пользователя <@{user_id}> по причине:\n\n{self.reason}."  # noqa: E501
            case RoleRequestStateEnum.CANCELED:
                header_text = "### <:9349_nope:1414732960841859182> | CANCELED"
                if moderator_id:
                    header_text += f"<:42920arrowrightalt:1421170550759489616> <@{moderator_id}>"  # noqa: E501
                text = (
                    f"Пользователь <@{user_id}> отклонил свой запрос на роль."
                )
            case RoleRequestStateEnum.EXPIRED:
                header_text = "### <:9349_nope:1414732960841859182> | EXPIRED"
                if moderator_id:
                    header_text += f"<:42920arrowrightalt:1421170550759489616> <@{moderator_id}>"  # noqa: E501
                text = f"Запрос пользователя <@{user_id}> истек и был удален."
            case _:
                ...

        container.add_item(TextDisplay(header_text))
        container.add_item(Separator())
        container.add_item(TextDisplay(text))
        container.add_item(Separator())

        if _is_stats and message_url and image_url and image_proxy_url:
            container.add_item(
                LinksActionRow(
                    message_url=message_url,
                    image_url=image_url,
                    image_proxy_url=image_proxy_url,
                )
            )
            container.add_item(Separator())

        now = datetime.now(timezone.utc)

        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}\n"  # type: ignore
            )
        )

        self.add_item(container)
