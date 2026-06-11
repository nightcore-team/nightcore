"""Command to get a user's banner."""

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

logger = logging.getLogger(__name__)


class Banner(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(
        name="banner", description="Получить баннер пользователя"
    )
    @app_commands.describe(user="Пользователь, чей баннер нужно получить")
    @check_required_permissions(PermissionsFlagEnum.NONE)
    async def banner(
        self,
        interaction: Interaction,
        user: User | Member | None = None,
        ephemeral: bool = True,
    ):
        """Send a message displaying the user's banner."""

        if user is None:
            u = interaction.user
        else:
            u = self.bot.get_user(user.id)
            if u is None:
                try:
                    u = await self.bot.fetch_user(user.id)
                except discord.NotFound:
                    await interaction.response.send_message(
                        "Пользователь не найден.",
                        ephemeral=True,
                    )
                    return

        if u.banner:
            await interaction.response.send_message(
                embed=Embed(
                    title=f"Баннер пользователя {u.display_name}",
                    color=discord.Color.blurple(),
                ).set_image(url=u.banner.url),
                ephemeral=ephemeral,
            )

        else:
            await interaction.response.send_message(
                "У пользователя нет баннера.",
                ephemeral=True,
            )

        logger.info(
            "[command] - invoked user=%s guild=%s target=%s",
            interaction.user.id,
            interaction.guild.id if interaction.guild else None,
            u.id,
        )


async def setup(bot: Nightcore):
    """Setup the Banner cog."""
    await bot.add_cog(Banner(bot))
