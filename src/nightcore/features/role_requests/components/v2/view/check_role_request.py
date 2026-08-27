"""View for sending role requests."""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self

from discord import ButtonStyle, Color, MediaGalleryItem
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    MediaGallery,
    Separator,
    TextDisplay,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import discord_ts
from src.utils._enums import RoleRequestStateEnum

logger = logging.getLogger(__name__)


class ManageRoleRequestActionRow(ActionRow["CheckRoleRequestView"]):
    def __init__(self) -> None:
        super().__init__()

        self.add_item(
            Button["CheckRoleRequestView"](
                label="Одобрить запрос",
                custom_id="role_request:approve",
                style=ButtonStyle.grey,
                emoji="<:nightcoreAcceptGreen:1540739795737780355>",
            )
        )

        self.add_item(
            Button["CheckRoleRequestView"](
                label="Отклонить запрос",
                custom_id="role_request:decline",
                style=ButtonStyle.grey,
                emoji="<:nightcoreDeclineRed:1540733707416117388>",
            )
        )


class CheckRoleRequestView(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        interaction_user_id: int | None = None,
        interaction_user_nick: str | None = None,
        role_requested_id: int | None = None,
        moderator_id: int | None = None,
        state: RoleRequestStateEnum | None = None,
        attachments: list[MediaGalleryItem] | None = None,
        all_disabled: bool = False,
    ) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.interaction_user_id = interaction_user_id
        self.role_requested_id = role_requested_id
        self.moderator_id = moderator_id
        self.interaction_user_nick = interaction_user_nick
        self.state = state
        self.attachments = attachments

        self.actions: ManageRoleRequestActionRow

        self.make_component(all_disabled)

    def disable_buttons(self):
        """Disable all buttons in the view."""
        if self.actions:
            for item in self.actions.children:
                if isinstance(item, Button):
                    item.disabled = True  # type: ignore

    def make_component(self, disable_all: bool = False) -> Self:
        """Create view."""
        self.clear_items()

        container = Container[Self]()

        # header
        container.add_item(TextDisplay[Self]("## Запрос на роль"))
        container.add_item(Separator[Self]())

        text = (
            f"**Пользователь**: <@{self.interaction_user_id}> (`{self.interaction_user_id}`)\n"  # noqa: E501
            f"**Запрашиваемая роль**: <@&{self.role_requested_id}>\n"
        )
        if self.interaction_user_nick:
            text = (
                f"**Пользователь**: <@{self.interaction_user_id}> (`{self.interaction_user_id}`)\n"  # noqa: E501
                f"**Никнейм**: {self.interaction_user_nick}\n"
                f"**Запрашиваемая роль**: <@&{self.role_requested_id}>\n"
            )

        # main text
        container.add_item(TextDisplay[Self](text))
        container.add_item(Separator[Self]())

        accent_color: Color | None = None
        # state
        if self.state:
            state_str = ""
            match self.state:
                case RoleRequestStateEnum.APPROVED:
                    accent_color = Color.from_str("#81b475")
                    state_str = f"Запрос на статистику был **одобрен** модератором: <@{self.moderator_id}>"  # noqa: E501
                case RoleRequestStateEnum.DENIED:
                    accent_color = Color.from_str("#C0577A")
                    state_str = f"Запрос на статистику был **отклонен** модератором: <@{self.moderator_id}>"  # noqa: E501
                case RoleRequestStateEnum.CANCELED:
                    accent_color = Color.from_str("#C0577A")
                    state_str = "Пользователь отменил свой запрос на роль."
                    self.moderator_id = None
                case RoleRequestStateEnum.EXPIRED:
                    accent_color = Color.from_str("#CACA47")
                    state_str = "Запрос на роль **истек**."
                    self.moderator_id = None
                case _:
                    state_str = "Cannot determine state."

            container.add_item(TextDisplay[Self](f"{state_str}"))
            container.add_item(Separator[Self]())

        if accent_color:
            container._colour = accent_color  # type: ignore

        if self.attachments:
            # attachments
            gallery = MediaGallery[Self](*self.attachments)
            container.add_item(gallery)
            container.add_item(Separator[Self]())

        # manage buttons
        self.actions = ManageRoleRequestActionRow()
        container.add_item(self.actions)
        container.add_item(Separator[Self]())

        if disable_all:
            self.disable_buttons()

        # footer
        now = datetime.now(UTC)

        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}\n"  # type: ignore
            )
        )

        self.add_item(container)

        return self
