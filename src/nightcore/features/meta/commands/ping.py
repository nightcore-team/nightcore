"""Command to check bot latency."""

from typing import TYPE_CHECKING

from discord import app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.decorators.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)


from src.nightcore.decorators.time_executing import time_executing


class Ping(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(name="ping", description="Посмотреть задержку бота")
    @check_required_permissions(PermissionsFlagEnum.NONE)
    @time_executing
    async def ping(self, interaction: Interaction):
        """Send a message displaying the bot's current latency."""

        await interaction.response.send_message(
            f"Pong! Latency: {self.bot.latency * 1000:.2f} ms", ephemeral=True
        )


async def setup(bot: "Nightcore"):
    """Setup the Ping cog."""
    await bot.add_cog(Ping(bot))
