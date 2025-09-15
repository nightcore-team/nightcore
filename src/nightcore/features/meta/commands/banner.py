"""Avatar command for the Nightcore bot."""

import logging

import discord
from discord import Embed, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class Banner(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(name="banner", description="Get user's banner")
    @app_commands.describe(user="The user to get the banner of.")
    async def banner(
        self,
        interaction: Interaction,
        user: discord.User | None = None,
    ):
        """Send a message displaying the user's banner."""

        if user is None:
            u = interaction.user  # type: ignore
        else:
            u = self.bot.get_user(user.id)  # type: ignore
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
                    title=f"Баннер пользователя {user.display_name}",  # type: ignore
                    color=discord.Color.blurple(),
                ).set_image(
                    url=u.banner.url  # type: ignore
                ),
                ephemeral=True,
            )

        else:
            await interaction.response.send_message(
                "У пользователя нет баннера.",  # noqa: RUF001
                ephemeral=True,
            )
        logger.info(
            "[command] - invoked user=%s guild=%s target=%s",
            interaction.user.id,  # type: ignore
            interaction.guild.id if interaction.guild else None,
            user.id,  # type: ignore
        )


async def setup(bot: Nightcore):
    """Setup the Banner cog."""
    await bot.add_cog(Banner(bot))
