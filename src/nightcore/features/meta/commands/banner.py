"""Command to get a user's banner."""

import logging

import discord
from discord import Embed, User, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.nightcore.bot import Nightcore
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


class Banner(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(  # type: ignore
        name="banner", description="Получить баннер пользователя"
    )
    @app_commands.describe(user="Пользователь, чей баннер нужно получить")
    @check_required_permissions(PermissionsFlagEnum.NONE)  # type: ignore
    async def banner(
        self,
        interaction: Interaction,
        user: User | None = None,
        ephemeral: bool = True,
    ):
        """Send a message displaying the user's banner."""
        target = user if user is not None else interaction.user

        try:
            fetched = await self.bot.fetch_user(target.id)  # type: ignore
        except discord.NotFound:
            await interaction.response.send_message(
                "Пользователь не найден.",
                ephemeral=True,
            )
            return
        except discord.HTTPException as e:
            logger.exception(
                "[command] - failed to fetch user %s: %s",
                target.id,  # type: ignore
                e,
            )
            await interaction.response.send_message(
                "Не удалось получить информацию о пользователе.",
                ephemeral=True,
            )
            return

        if fetched.banner:
            await interaction.response.send_message(
                embed=Embed(
                    title=f"Баннер пользователя {fetched.display_name}",
                    color=discord.Color.from_str("#D896C8"),
                ).set_image(
                    url=fetched.banner.url
                ),
                ephemeral=ephemeral,
            )
        else:
            await interaction.response.send_message(
                "У пользователя нет баннера.",
                ephemeral=True,
            )
        logger.info(
            "[command] - invoked user=%s guild=%s target=%s",
            interaction.user.id,  # type: ignore
            interaction.guild.id if interaction.guild else None,
            fetched.id,
        )


async def setup(bot: Nightcore):
    """Setup the Banner cog."""
    await bot.add_cog(Banner(bot))
