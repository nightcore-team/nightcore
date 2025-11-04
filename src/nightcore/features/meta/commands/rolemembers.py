"""Command to get members of a role."""

import logging

import discord
from discord import app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.nightcore.bot import Nightcore
from src.nightcore.features.meta.components.v2 import RoleMembersViewV2
from src.nightcore.features.meta.utils import build_rolemembers_pages

logger = logging.getLogger(__name__)


class RoleMembers(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(
        name="rolemembers",
        description="Получить список участников с определённой ролью",
    )
    @app_commands.describe(role="Роль, участников которой нужно получить")
    async def role_members(
        self,
        interaction: Interaction,
        role: discord.Role,
        ephemeral: bool = True,
    ):
        """Send a message displaying the members of a role."""

        pages = build_rolemembers_pages(members=role.members)

        view = RoleMembersViewV2(
            bot=self.bot,
            role=role,
            pages=pages,
            members_count=len(role.members),
            author_id=interaction.user.id,
        )

        await interaction.response.send_message(
            view=view,
            ephemeral=ephemeral,
        )

        logger.info(
            "[command] - invoked user=%s guild=%s target=%s",
            interaction.user.id,  # type: ignore
            interaction.guild.id if interaction.guild else None,
            role.id,
        )


async def setup(bot: Nightcore):
    """Setup the RoleMembers cog."""
    await bot.add_cog(RoleMembers(bot))
