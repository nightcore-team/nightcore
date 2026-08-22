"""Error events module."""

import logging
from typing import cast

import discord
from discord import AppCommandOptionType, Guild, app_commands
from discord.ext import commands

from src.nightcore.bot import Nightcore
from src.nightcore.components.view.v2 import (
    EntityNotFoundViewV2,
    ErrorViewV2,
    MissingPermissionsViewV2,
    NoConfigFoundButCreatedViewV2,
    NoConfigFoundViewV2,
    StrToIntTransformFailedViewV2,
    ValidationErrorViewV2,
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
from src.nightcore.utils.transformers.str_to_int import StrToIntTransformer

logger = logging.getLogger(__name__)


async def setup(bot: "Nightcore") -> None:
    """Setup the error handling for commands."""

    @bot.event
    async def on_command_error(  # type: ignore
        ctx: commands.Context[Nightcore],
        error: commands.CommandError,
    ):
        """Handle text command errors."""

        original = getattr(error, "original", error)

        if isinstance(original, commands.CommandNotFound):
            return

        logger.exception("Unhandled text command error", exc_info=error)
        await ctx.send(
            "Unexpected error occurred. Please contact the developer.",
        )

    @bot.tree.error
    async def on_app_command_error(  # type: ignore
        interaction: discord.Interaction[Nightcore],
        error: app_commands.AppCommandError,
    ):
        """Handle application command errors."""

        original = getattr(error, "original", error)

        if isinstance(original, ConfigMissingButCreatingError):
            logger.info(
                "%s handled guild=%s user=%s",
                original.__class__.__name__,
                cast(Guild, interaction.guild).id,
                interaction.user.id,
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    view=NoConfigFoundButCreatedViewV2(),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    view=NoConfigFoundButCreatedViewV2(),
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
                        view=StrToIntTransformFailedViewV2(original.value),
                        ephemeral=True,
                    )
                else:
                    await interaction.followup.send(
                        view=StrToIntTransformFailedViewV2(original.value),
                        ephemeral=True,
                    )
                return

            if original.type == AppCommandOptionType.user:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        view=EntityNotFoundViewV2("пользователь"),
                        ephemeral=True,
                    )
                else:
                    await interaction.followup.send(
                        view=EntityNotFoundViewV2("пользователь"),
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
                    view=MissingPermissionsViewV2(
                        "Вам не хватает следующих прав для "
                        f"использования этой команды: {missing_perms}."
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    view=MissingPermissionsViewV2(
                        "Вам не хватает следующих прав для "
                        f"использования этой команды: {missing_perms}."
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
                    view=ErrorViewV2(
                        "Команда на перезарядке",
                        f"Пожалуйста, подождите {original.retry_after:.2f} "
                        "секунд перед повторным использованием этой команды.",
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    view=ErrorViewV2(
                        "Команда на перезарядке",
                        f"Пожалуйста, подождите {original.retry_after:.2f} "
                        "секунд перед повторным использованием этой команды.",
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
                    view=NoConfigFoundViewV2(),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    view=NoConfigFoundViewV2(),
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
                    view=ValidationErrorViewV2(
                        f"{original.__class__.__name__}: {original.msg}"
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    view=ValidationErrorViewV2(
                        f"{original.__class__.__name__}: {original.msg}"
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
                    view=ValidationErrorViewV2(
                        f"{original.__class__.__name__}: {original.msg}"
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    view=ValidationErrorViewV2(
                        f"{original.__class__.__name__}: {original.msg}"
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
                    view=ValidationErrorViewV2(
                        f"{original.__class__.__name__}: {original.msg}"
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    view=ValidationErrorViewV2(
                        f"{original.__class__.__name__}: {original.msg}"
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
                    view=ErrorViewV2(
                        "Нужный параметр не настроен", f"{original}"
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    view=ErrorViewV2(
                        "Нужный параметр не настроен.", f"{original}"
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
