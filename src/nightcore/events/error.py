"""Error events module."""

import logging

import discord
from discord import app_commands

from src.nightcore.bot import Nightcore
from src.nightcore.components.embed.error import NoConfigFoundEmbed
from src.nightcore.exceptions import ConfigMissingError

logger = logging.getLogger(__name__)


async def setup(bot: Nightcore):
    @bot.tree.error
    async def on_app_command_error(
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ):
        """Handle application command errors."""

        original = getattr(error, "original", error)

        if isinstance(original, ConfigMissingError):
            logger.info(
                "ConfigMissingError handled guild=%s user=%s",
                interaction.guild.id,  # type: ignore
                interaction.user.id,  # type: ignore
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    embed=NoConfigFoundEmbed(),
                    ephemeral=True,
                )
            return

        # logger.exception("Unhandled app command error", exc_info=original)
        # if not interaction.response.is_done():
        #     await interaction.response.send_message(
        #         "Сталася неочікувана помилка. Повідом адміністратора.",
        #         ephemeral=True,
        #     )
