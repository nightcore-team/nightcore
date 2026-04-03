"""Command to check bot latency."""

from typing import TYPE_CHECKING

from discord import Attachment, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)


class Say(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(
        name="say", description="Отправить сообщение от бота"
    )  # type: ignore
    @check_required_permissions(PermissionsFlagEnum.BOT_ACCESS)  # type: ignore
    async def say(
        self,
        interaction: Interaction["Nightcore"],
        text: str,
        image: Attachment | None = None,
    ) -> None:
        """Send a message displaying the bot's current latency."""
        await interaction.channel.send(text, file=image)  # type: ignore

        await interaction.response.send_message(
            "Сообщение отправлено!", ephemeral=True
        )


async def setup(bot: "Nightcore"):
    """Setup the Say cog."""
    await bot.add_cog(Say(bot))
