"""Avatar command for the Nightcore bot."""

import logging

import discord
from discord import Embed, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class Avatar(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(name="avatar", description="Get user's avatar")
    @app_commands.describe(user="The user to get the avatar of.")
    async def avatar(
        self,
        interaction: Interaction,
        user: discord.Member | discord.User | None = None,
        ephemeral: bool = True,
    ):
        """Send a message displaying the user's avatar."""

        if user is None:
            user = interaction.user  # type: ignore

        await interaction.response.send_message(
            embed=Embed(
                title=f"Аватар пользователя {user.display_name}",  # type: ignore
                color=discord.Color.blurple(),
            ).set_image(
                url=user.avatar.url  # type: ignore
                if user.avatar  # type: ignore
                else user.default_avatar.url  # type: ignore
            ),
            ephemeral=ephemeral,
        )

        logger.info(
            "[command] - invoked user=%s guild=%s target=%s",
            interaction.user.id,  # type: ignore
            interaction.guild.id if interaction.guild else None,
            user.id,  # type: ignore
        )


async def setup(bot: Nightcore):
    """Setup the Avatar cog."""
    await bot.add_cog(Avatar(bot))
