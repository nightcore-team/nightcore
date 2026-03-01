"""Error events module."""

import logging
from typing import TYPE_CHECKING, cast

import discord
from discord import AppCommandOptionType, Guild, app_commands
from discord.ext import commands

from src.nightcore.utils.transformers.str_to_int import StrToIntTransformer

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.components.embed.error import (
    EntityNotFoundEmbed,
    ErrorEmbed,
    MissingPermissionsEmbed,
    NoConfigFoundButCreatedEmbed,
    NoConfigFoundEmbed,
    StrToIntTransformFailedEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.exceptions import (
    ConfigMissingButCreatingError,
    ConfigMissingError,
    FieldNotConfiguredError,
)
from src.nightcore.features.config.exceptions import (
    LevelRolesParsingError,
    OrgRolesParsingError,
    TempVoiceRolesParsingError,
)

logger = logging.getLogger(__name__)


async def setup(bot: "Nightcore") -> None:
    """Setup the error handling for application commands."""

    @bot.tree.error
    async def on_app_command_error(  # type: ignore
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ):
        """Handle application command errors."""

        original = getattr(error, "original", error)

        if isinstance(original, commands.CommandNotFound):
            return

        if isinstance(original, ConfigMissingButCreatingError):
            logger.info(
                "%s handled guild=%s user=%s",
                original.__class__.__name__,
                cast(Guild, interaction.guild).id,
                interaction.user.id,
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    embed=NoConfigFoundButCreatedEmbed(
                        interaction.client.user.name,  # type: ignore
                        interaction.client.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    embed=NoConfigFoundButCreatedEmbed(
                        interaction.client.user.name,  # type: ignore
                        interaction.client.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
            return

        if isinstance(original, app_commands.TransformerError):
            logger.info(
                "%s handled guild=%s user=%s",
                original.__class__.__name__,
                cast(Guild, interaction.guild).id,
                interaction.user.id,
            )

            if isinstance(original.transformer, StrToIntTransformer):
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        embed=StrToIntTransformFailedEmbed(
                            original.value,
                            interaction.client.user.name,  # type: ignore
                            interaction.client.user.display_avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
                else:
                    await interaction.followup.send(
                        embed=StrToIntTransformFailedEmbed(
                            original.value,
                            interaction.client.user.name,  # type: ignore
                            interaction.client.user.display_avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
                return

            if original.type == AppCommandOptionType.user:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        embed=EntityNotFoundEmbed(
                            "пользователь",
                            interaction.client.user.name,  # type: ignore
                            interaction.client.user.display_avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
                else:
                    await interaction.followup.send(
                        embed=EntityNotFoundEmbed(
                            "пользователь",
                            interaction.client.user.name,  # type: ignore
                            interaction.client.user.display_avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
                return

        if isinstance(original, app_commands.MissingPermissions):
            logger.info(
                "%s handled guild=%s user=%s",
                original.__class__.__name__,
                cast(Guild, interaction.guild).id,
                interaction.user.id,
            )
            missing_perms = ", ".join(original.missing_permissions)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    embed=MissingPermissionsEmbed(
                        interaction.client.user.name,  # type: ignore
                        interaction.client.user.display_avatar.url,  # type: ignore
                        f"Вам не хватает следующих прав для использования этой команды: {missing_perms}.",  # noqa: E501
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    embed=MissingPermissionsEmbed(
                        interaction.client.user.name,  # type: ignore
                        interaction.client.user.display_avatar.url,  # type: ignore
                        f"Вам не хватает следующих прав для использования этой команды: {missing_perms}.",  # noqa: E501
                    ),
                    ephemeral=True,
                )
            return

        if isinstance(original, app_commands.CommandOnCooldown):
            logger.info(
                "%s handled guild=%s user=%s retry_after=%.2fs",
                original.__class__.__name__,
                cast(Guild, interaction.guild).id,
                interaction.user.id,
                original.retry_after,
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Команда на перезарядке",
                        f"Пожалуйста, подождите {original.retry_after:.2f} секунд перед повторным использованием этой команды.",  # noqa: E501
                        interaction.client.user.name,  # type: ignore
                        interaction.client.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Команда на перезарядке",
                        f"Пожалуйста, подождите {original.retry_after:.2f} секунд перед повторным использованием этой команды.",  # noqa: E501
                        interaction.client.user.name,  # type: ignore
                        interaction.client.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
            return

        if isinstance(original, ConfigMissingError):
            logger.info(
                "%s handled guild=%s user=%s",
                original.__class__.__name__,
                cast(Guild, interaction.guild).id,
                interaction.user.id,
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    embed=NoConfigFoundEmbed(
                        interaction.client.user.name,  # type: ignore
                        interaction.client.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    embed=NoConfigFoundEmbed(
                        interaction.client.user.name,  # type: ignore
                        interaction.client.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
            return

        if isinstance(original, OrgRolesParsingError):
            logger.info(
                "%s handled guild=%s user=%s msg=%s",
                original.__class__.__name__,
                cast(Guild, interaction.guild).id,
                interaction.user.id,
                original.msg,
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    embed=ValidationErrorEmbed(
                        f"{original.__class__.__name__}: {original.msg}",
                        interaction.client.user.name,  # type: ignore
                        interaction.client.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    embed=ValidationErrorEmbed(
                        f"{original.__class__.__name__}: {original.msg}",
                        interaction.client.user.name,  # type: ignore
                        interaction.client.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
            return

        if isinstance(original, TempVoiceRolesParsingError):
            logger.info(
                "%s handled guild=%s user=%s msg=%s",
                original.__class__.__name__,
                cast(Guild, interaction.guild).id,
                interaction.user.id,
                original.msg,
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    embed=ValidationErrorEmbed(
                        f"{original.__class__.__name__}: {original.msg}",
                        interaction.client.user.name,  # type: ignore
                        interaction.client.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    embed=ValidationErrorEmbed(
                        f"{original.__class__.__name__}: {original.msg}",
                        interaction.client.user.name,  # type: ignore
                        interaction.client.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
            return

        if isinstance(original, LevelRolesParsingError):
            logger.info(
                "%s handled guild=%s user=%s msg=%s",
                original.__class__.__name__,
                cast(Guild, interaction.guild).id,
                interaction.user.id,
                original.msg,
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    embed=ValidationErrorEmbed(
                        f"{original.__class__.__name__}: {original.msg}",
                        interaction.client.user.name,  # type: ignore
                        interaction.client.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    embed=ValidationErrorEmbed(
                        f"{original.__class__.__name__}: {original.msg}",
                        interaction.client.user.name,  # type: ignore
                        interaction.client.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
            return

        if isinstance(original, FieldNotConfiguredError):
            logger.info(
                "%s handled guild=%s user=%s msg=%s",
                original.__class__.__name__,
                cast(Guild, interaction.guild).id,
                interaction.user.id,
                str(original),
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Нужный параметр не настроен",
                        f"{original}",
                        interaction.client.user.name,  # type: ignore
                        interaction.client.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Нужный параметр не настроен.",
                        f"{original}",
                        interaction.client.user.name,  # type: ignore
                        interaction.client.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
            return

        logger.exception("Unhandled app command error", exc_info=error)
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "Unexpected error occurred. Please contact the developer.",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                "Unexpected error occurred. Please contact the developer.",
                ephemeral=True,
            )
