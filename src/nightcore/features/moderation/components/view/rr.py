"""View for removing organization roles via a dropdown menu."""

import logging
from datetime import timezone
from typing import TYPE_CHECKING

import discord

from src.nightcore.components.embed import (
    ErrorEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.features.moderation.events.dto import (
    RolesChangeEventData,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class RemoveOrgRoleSelect(discord.ui.View):
    def __init__(
        self,
        bot: "Nightcore",
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
            max_values=len(roles),
            options=options,
        )
        self.select.callback = self._select_callback  # type: ignore
        self.add_item(self.select)

    async def _select_callback(self, interaction: discord.Interaction):
        roles = list(map(int, self.select.values))

        roles = [role for role in self.member.roles if role.id in roles]

        try:
            await self.member.remove_roles(
                *roles,
                reason="Снятие организационных ролей через /rr",
                atomic=False,
            )
        except Exception as e:
            logger.exception("[command] - Failed to remove role: %s", e)
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка снятия ролей",
                    "Не удалось снять указанные роли с пользователя.",
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
                    role=roles[0],
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
                child.disabled = True  # type: ignore

        await interaction.response.edit_message(
            embed=SuccessMoveEmbed(
                "Role Removed",
                f"Role {','.join(role.mention for role in roles)} successfully removed from {self.member.mention}.",  # noqa: E501
                self.bot.user.name,  # type: ignore
                self.bot.user.display_avatar.url,  # type: ignore
            ),
            view=self,
        )
