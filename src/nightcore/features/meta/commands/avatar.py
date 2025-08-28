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
    @app_commands.describe(member="The member to get the avatar of.")
    async def avatar(
        self,
        interaction: Interaction,
        member: discord.Member | discord.User | None = None,
    ):
        """Send a message displaying the user's avatar."""

        if member is None:
            member = interaction.user  # type: ignore

        await interaction.response.send_message(
            embed=Embed(
                title=f"Аватар пользователя {member.display_name}",  # type: ignore
                color=discord.Color.blurple(),
            ).set_image(
                url=member.avatar.url  # type: ignore
                if member.avatar  # type: ignore
                else member.default_avatar.url  # type: ignore
            ),
            ephemeral=True,
        )

        logger.info(
            "[command] - invoked user=%s guild=%s target=%s",
            interaction.user.id,  # type: ignore
            interaction.guild.id if interaction.guild else None,
            member.id,  # type: ignore
        )


async def setup(bot: Nightcore):
    """Setup the Avatar cog."""
    await bot.add_cog(Avatar(bot))
