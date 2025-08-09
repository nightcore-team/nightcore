"""Avatar command for the Nightcore bot."""

import logging

import discord
from discord import Embed, app_commands
from discord.ext.commands import Cog
from discord.interactions import Interaction, InteractionCallbackResponse

from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class Avatar(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(name="avatar", description="Get user's avatar")
    async def avatar(
        self,
        interaction: Interaction,
        member: discord.Member | discord.User | None = None,
    ) -> InteractionCallbackResponse:
        """Send a message displaying the user's avatar.

        Args:
            interaction : discord.Interaction
                The interaction that triggered the command.
            member :
                Выберите пользователя, чей аватар вы хотите получить.
        """

        if member is None:
            member = interaction.user

        response = await interaction.response.send_message(
            embed=Embed(
                title=f"Аватар пользователя {member.display_name}",
                color=discord.Color.blurple(),
            ).set_image(
                url=member.avatar.url
                if member.avatar
                else member.default_avatar.url
            ),
            ephemeral=True,
        )

        logger.info(
            "commands.avatar invoked user=%s guild=%s target=%s",
            interaction.user.id,
            interaction.guild.id if interaction.guild else None,
            member.id,
        )

        return response


async def setup(bot: Nightcore):
    """Setup the Avatar cog."""
    await bot.add_cog(Avatar(bot))
