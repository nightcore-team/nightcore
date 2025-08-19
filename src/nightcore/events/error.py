"""Error events module."""

import logging
from typing import cast

import discord
from discord import Guild, app_commands

from src.nightcore.bot import Nightcore
from src.nightcore.components.embed.error import (
    NoConfigFoundEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.exceptions import (
    ConfigMissingError,
)
from src.nightcore.features.config.exceptions import (
    LevelRolesParsingError,
    OrgRolesParsingError,
    TempVoiceRolesParsingError,
)

logger = logging.getLogger(__name__)


async def setup(bot: Nightcore):
    """Setup the error handling for application commands."""

    @bot.tree.error
    async def on_app_command_error(  # type: ignore
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ):
        """Handle application command errors."""

        original = getattr(error, "original", error)

        if isinstance(original, ConfigMissingError):
            logger.info(
                "%s handled guild=%s user=%s",
                original.__class__.__name__,
                cast(Guild, interaction.guild).id,
                interaction.user.id,
            )
            logger.exception(
                "%s occurred", original.__class__.__name__, exc_info=original
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    embed=NoConfigFoundEmbed(),
                    ephemeral=True,
                )
            return

        if isinstance(original, OrgRolesParsingError):
            logger.info(
                "%s handled guild=%s user=%s",
                original.__class__.__name__,
                cast(Guild, interaction.guild).id,
                interaction.user.id,
            )
            logger.exception(
                "%s occurred", original.__class__.__name__, exc_info=original
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    embed=ValidationErrorEmbed(
                        f"{original.__class__.__name__}: {original.msg}"
                    ),
                    ephemeral=True,
                )
            return

        if isinstance(original, TempVoiceRolesParsingError):
            logger.info(
                "%s handled guild=%s user=%s",
                original.__class__.__name__,
                cast(Guild, interaction.guild).id,
                interaction.user.id,
            )
            logger.exception(
                "%s occurred", original.__class__.__name__, exc_info=original
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    embed=ValidationErrorEmbed(
                        f"{original.__class__.__name__}: {original.msg}"
                    ),
                    ephemeral=True,
                )
            return

        if isinstance(original, LevelRolesParsingError):
            logger.info(
                "%s handled guild=%s user=%s",
                original.__class__.__name__,
                cast(Guild, interaction.guild).id,
                interaction.user.id,
            )
            logger.exception(
                "%s occurred", original.__class__.__name__, exc_info=original
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    embed=ValidationErrorEmbed(
                        f"{original.__class__.__name__}: {original.msg}"
                    ),
                    ephemeral=True,
                )
            return

        logger.exception("Unhandled app command error", exc_info=error)
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "Unexpected error occurred. Please contact the administrator.",
                ephemeral=True,
            )
