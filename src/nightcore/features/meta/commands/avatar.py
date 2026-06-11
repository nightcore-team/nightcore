"""Command to get a user's avatar."""

import logging

import discord
from discord import Embed, Member, User, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.nightcore.bot import Nightcore
from src.nightcore.decorators.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

from src.nightcore.decorators.time_executing import time_executing

logger = logging.getLogger(__name__)


class Avatar(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(
        name="avatar", description="Получить аватар пользователя"
    )
    @app_commands.describe(user="Пользователь, чей аватар нужно получить")
    @check_required_permissions(PermissionsFlagEnum.NONE)
    @time_executing
    async def avatar(
        self,
        interaction: Interaction,
        user: User | Member | None = None,
        ephemeral: bool = True,
    ):
        """Send a message displaying the user's avatar."""

        if user is None:
            user = interaction.user

        await interaction.response.send_message(
            embed=Embed(
                title=f"Аватар пользователя {user.display_name}",
                color=discord.Color.blurple(),
            ).set_image(
                url=user.avatar.url if user.avatar else user.default_avatar.url
            ),
            ephemeral=ephemeral,
        )

        logger.info(
            "[command] - invoked user=%s guild=%s target=%s",
            interaction.user.id,
            interaction.guild.id if interaction.guild else None,
            user.id,
        )


async def setup(bot: Nightcore):
    """Setup the Avatar cog."""
    await bot.add_cog(Avatar(bot))
