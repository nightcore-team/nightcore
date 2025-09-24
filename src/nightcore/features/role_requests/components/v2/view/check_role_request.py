"""View for sending role requests."""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self

from discord import ButtonStyle
from discord.interactions import Interaction
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    Separator,
    TextDisplay,
    button,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import discord_ts

logger = logging.getLogger(__name__)


class ManageRoleRequestActionRow(ActionRow["CheckRoleRequestView"]):
    @button(
        label="Request stats",
        custom_id="role_request:stats",
        style=ButtonStyle.grey,
        emoji="<:6344communicationrequests:1420132990327197862>",
    )  # TODO: implement
    async def request_stats(
        self,
        interaction: Interaction["Nightcore"],
        button: Button["CheckRoleRequestView"],
    ) -> None:
        """Handle the cancel button interaction."""
        await interaction.response.send_message(
            "You requested stats for this role.", ephemeral=True
        )

    @button(
        label="Approve request",
        custom_id="role_request:approve",
        style=ButtonStyle.success,
        emoji="<:52104checkmark:1414732973005340672>",
    )  # TODO: implement
    async def approve_role_request(
        self,
        interaction: Interaction["Nightcore"],
        button: Button["CheckRoleRequestView"],
    ) -> None:
        """Handle the cancel button interaction."""
        await interaction.response.send_message(
            "You approved the role request.", ephemeral=True
        )

    @button(
        label="Decline request",
        custom_id="role_request:decline",
        style=ButtonStyle.danger,
        emoji="<:9349_nope:1414732960841859182>",
    )  # TODO: implement
    async def decline_role_request(
        self,
        interaction: Interaction["Nightcore"],
        button: Button["CheckRoleRequestView"],
    ) -> None:
        """Handle the cancel button interaction."""
        await interaction.response.send_message(
            "You cancelled the role request.", ephemeral=True
        )


# TODO: add attachments
class CheckRoleRequestView(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        interaction_user_id: int | None = None,
        role_requested_id: int | None = None,
    ) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.interaction_user_id = interaction_user_id
        self.role_requested_id = role_requested_id

        container = Container[Self]()

        # header
        container.add_item(TextDisplay[Self]("## Role Request"))
        container.add_item(Separator[Self]())

        # main text
        container.add_item(
            TextDisplay[Self](
                f"User | ID: <@{self.interaction_user_id}> | {self.interaction_user_id}"  # noqa: E501
            )
        )
        container.add_item(
            TextDisplay[Self](f"Role requested: <@&{self.role_requested_id}>")
        )
        # select

        container.add_item(Separator[Self]())

        # manage buttons
        container.add_item(ManageRoleRequestActionRow())
        container.add_item(Separator[Self]())

        # footer
        now = datetime.now(timezone.utc)

        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}\n"  # type: ignore
            )
        )

        self.add_item(container)
