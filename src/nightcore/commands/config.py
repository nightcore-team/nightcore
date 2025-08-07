"""Config command for the Nightcore bot."""

import discord
from discord import Embed, app_commands
from discord.ext.commands import Cog
from discord.interactions import InteractionCallbackResponse

from src.infra.db.operations import get_guild_config
from src.nightcore.bot import Nightcore


class Config(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    config = app_commands.Group(
        name="config",
        description="Configuration commands for the Nightcore bot.",
    )

    @app_commands.checks.has_permissions(administrator=True)
    @config.command(
        name="check",
        description="Check if the config is synced with the database.",
    )
    async def check(
        self, interaction: discord.Interaction
    ) -> InteractionCallbackResponse:
        """Check if the config is synced with the database."""
        async with self.bot.uow.start() as uow:
            config = await get_guild_config(
                uow.session,  # type: ignore
                guild_id=interaction.guild_id,  # type: ignore
            )
        if config:
            description = f"Config is synced with the database for guild ID: {interaction.guild_id}.\n"  # type: ignore
        else:
            description = "Your config will be added to the database."

        return await interaction.response.send_message(
            embed=Embed(
                title="Config Check",
                description=description,
                color=discord.Color.green(),
            )
        )
