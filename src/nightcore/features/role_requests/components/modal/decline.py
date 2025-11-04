"""Modal for submitting ban requests."""

import asyncio
import logging
from typing import TYPE_CHECKING, Self, cast

import discord
from discord.ui import Modal, TextInput

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore
    from src.nightcore.features.role_requests.components.v2.view.check_role_request import (  # noqa: E501
        CheckRoleRequestView,
    )
    from src.nightcore.features.role_requests.components.v2.view.role_request_state import (  # noqa: E501
        RoleRequestStateView,
    )

from src.infra.db.models._enums import RoleRequestStateEnum
from src.infra.db.operations import get_latest_user_role_request
from src.nightcore.components.embed import (
    ErrorEmbed,
)
from src.nightcore.features.role_requests.utils import (
    send_role_request_dm,
)

logger = logging.getLogger(__name__)


class DeclineRoleRequestModal(Modal, title="Отклонить запрос роли"):
    reason = TextInput[Self](
        label="Введите причину отклонения",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=200,
    )

    def __init__(
        self,
        bot: "Nightcore",
        user: discord.Member,
        nightcore_notifications_channel_id: int | None,
        view: "CheckRoleRequestView",
        state_view: type["RoleRequestStateView"],
        message: discord.Message,
    ):
        super().__init__()
        self.user = user
        self.bot = bot
        self.nightcore_notifications_channel_id = (
            nightcore_notifications_channel_id
        )
        self.view = view
        self.state_view_type = state_view
        self.message = message

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Handles the submission of the ban form modal."""
        guild = cast(discord.Guild, interaction.guild)

        reason = self.reason.value

        await interaction.response.defer()

        outcome = ""
        async with self.bot.uow.start() as session:
            last_rr = await get_latest_user_role_request(
                session, guild_id=guild.id, user_id=self.user.id
            )
            if not last_rr:
                outcome = "role_request_not_found"
                logger.warning(
                    "No role request found for user %s in guild %s when declining",  # noqa: E501
                    self.user.id,
                    guild.id,
                )
            else:
                if last_rr.state == RoleRequestStateEnum.DENIED:
                    outcome = "role_request_already_declined"
                    logger.warning(
                        "Role request for user %s in guild %s is already declined",  # noqa: E501
                        self.user.id,
                        guild.id,
                    )

            if not outcome:
                last_rr.state = RoleRequestStateEnum.DENIED  # type: ignore
                last_rr.moderator_id = interaction.user.id  # type: ignore

        if outcome == "role_request_not_found":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Decline failed",
                    "Role request not found in database.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "role_request_already_declined":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Decline failed",
                    "Role request has already been declined.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        try:
            await self.message.edit(view=self.view)
        except Exception as e:
            logger.error(
                "Failed to edit role request message %s in guild %s: %s",
                self.message.id,
                guild.id,
                e,
            )
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Decline failed",
                    "An error occurred while editing the role request message.",  # noqa: E501
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        state_view = self.state_view_type(
            bot=self.bot,
            moderator_id=interaction.user.id,
            user_id=self.user.id,
            role_id=self.view.role_requested_id,
            state=RoleRequestStateEnum.DENIED,
            reason=reason,
        )
        await asyncio.gather(
            interaction.followup.send(view=state_view),
            send_role_request_dm(
                moderator_id=interaction.user.id,
                reserve_channel=self.nightcore_notifications_channel_id,
                user=self.user,
                state=RoleRequestStateEnum.DENIED,
                reason=reason,
            ),
        )

        logger.info(
            "Moderator %s declined role request from user %s in guild %s",
            interaction.user.id,
            self.view.interaction_user_id,
            guild.id,
        )
