"""Command to join a voice channel with the bot."""

from typing import TYPE_CHECKING

from discord import VoiceChannel, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.config.config import config as project_config
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)


class Join(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(
        name="join", description="Заставить бота зайти в голосовой канал"
    )  # type: ignore
    @check_required_permissions(PermissionsFlagEnum.UNSAFE)  # type: ignore
    async def join(
        self,
        interaction: Interaction["Nightcore"],
        channel: VoiceChannel,
    ) -> None:
        """Send a message displaying the bot's current latency."""

        if interaction.user.id not in project_config.bot.DEVELOPER_IDS:
            raise app_commands.MissingPermissions(["developer_access"])

        await channel.connect()

        await interaction.response.send_message(
            f"Бот зашел в голосовой канал {channel.name}", ephemeral=True
        )


async def setup(bot: "Nightcore"):
    """Setup the Join cog."""
    await bot.add_cog(Join(bot))
