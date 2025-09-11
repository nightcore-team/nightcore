"""View for removing organization roles via a dropdown menu."""

import logging
from datetime import timezone

import discord

from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import (
    EntityNotFoundEmbed,
    ErrorEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.features.moderation.events.dto import (
    RolesChangeEventData,
)

logger = logging.getLogger(__name__)


class RemoveOrgRoleSelect(discord.ui.View):
    def __init__(
        self,
        bot: Nightcore,
        member: discord.Member,
        roles: list[discord.Role],
        moderator: discord.Member,
        category: str,
    ):
        super().__init__(timeout=60)
        self.bot = bot
        self.member = member
        self.roles = roles
        self.moderator = moderator
        self.category = category

        options = [
            discord.SelectOption(label=role.name, value=str(role.id))
            for role in roles
        ]

        self.select = discord.ui.Select["RemoveOrgRoleSelect"](
            placeholder="Choose a role to remove",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.select.callback = self._select_callback  # type: ignore
        self.add_item(self.select)

    async def _select_callback(self, interaction: discord.Interaction):
        role_id = int(self.select.values[0])
        role = discord.utils.get(self.roles, id=role_id)
        if role is None:
            return await interaction.response.send_message(
                embed=EntityNotFoundEmbed(
                    "role",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        try:
            await self.member.remove_roles(
                role, reason="Organization role removal via /rr"
            )
        except Exception as e:
            logger.exception("[command] - Failed to remove role: %s", e)
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Role Removal Failed",
                    "Failed to remove role.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        try:
            self.bot.dispatch(
                "roles_change",
                data=RolesChangeEventData(
                    category="role_remove",
                    moderator=interaction.user,  # type: ignore
                    user=self.member,
                    role=role,
                    created_at=discord.utils.utcnow().astimezone(
                        tz=timezone.utc
                    ),
                ),
                _send_to_rr_channel=True,
            )
        except Exception as e:
            logger.exception(
                "[event] - Failed to dispatch roles_change event: %s", e
            )
            return

        # disable select after choice
        for child in self.children:
            if isinstance(child, discord.ui.Select):
                child.disabled = True

        await interaction.response.edit_message(
            embed=SuccessMoveEmbed(
                "Role Removed",
                f"Role {role.mention} successfully removed from {self.member.mention}.",  # noqa: E501
                self.bot.user.name,  # type: ignore
                self.bot.user.display_avatar.url,  # type: ignore
            ),
            view=self,
        )
