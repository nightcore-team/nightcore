"""Ping command for the Nightcore bot."""

from discord import app_commands
from discord.ext.commands import Cog
from discord.interactions import Interaction, InteractionCallbackResponse

from src.nightcore.bot import Nightcore


class Ping(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(name="ping", description="Check the bot's latency.")
    async def ping(
        self, interaction: Interaction
    ) -> InteractionCallbackResponse:
        """Send a message displaying the bot's current latency.

        Args:
            interaction : discord.Interaction
                The interaction that triggered the command.
        """
        return await interaction.response.send_message(
            f"Pong! Latency: {self.bot.latency * 1000:.2f} ms"
        )


async def setup(bot: Nightcore):
    """Setup the Ping cog."""
    await bot.add_cog(Ping(bot))
