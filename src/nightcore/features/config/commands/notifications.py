"""Moderstats configuration commands for the Nightcore bot."""

import logging
from typing import cast

import discord
from discord import Guild, app_commands
from discord.embeds import Embed
from discord.interactions import Interaction

from src.infra.db.models.guild import GuildNotificationsConfig
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import NoOptionsSuppliedEmbed
from src.nightcore.features.config._groups import config as main_config_group
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.field_validators import (
    FieldSpec,
    apply_field_changes,
    format_changes,
    int_id_value,
    split_changes,
)

logger = logging.getLogger(__name__)


@main_config_group.command(
    name="notifications", description="Configure notifications settings."
)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    notifications="The channel to send notifications (/notify)",
    moderation_notifications="The channel to send moderation notifications",
    nightcore_notifications="The channel to send Nightcore notifications",
)
async def notifications(
    interaction: Interaction,
    notifications: discord.TextChannel | None = None,
    moderation_notifications: discord.TextChannel | None = None,
    nightcore_notifications: discord.TextChannel | None = None,
):
    """Configure notifications settings."""

    specs: list[FieldSpec | None] = [
        int_id_value("notifications_channel_id", notifications),
        int_id_value(
            "notifications_for_moderation_channel_id", moderation_notifications
        ),
        int_id_value(
            "notifications_from_bot_channel_id", nightcore_notifications
        ),
    ]

    specs = [s for s in specs if s is not None]

    if not specs:
        logger.info(
            "config.notifications invoked user=%s guild=%s no_options_supplied",  # noqa: E501
            interaction.user.id,  # type: ignore
            interaction.guild.id,  # type: ignore
        )
        return await interaction.response.send_message(
            embed=NoOptionsSuppliedEmbed(
                interaction.client.user.name,  # type: ignore
                interaction.client.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    async with specified_guild_config(
        cast(Nightcore, interaction.client),
        cast(Guild, interaction.guild).id,
        config_type=GuildNotificationsConfig,
    ) as guild_config:
        changes = apply_field_changes(guild_config, specs)  # type: ignore

    changed, skipped = split_changes(changes)
    description = format_changes(changed, skipped)

    logger.info(
        "config.notifications invoked user=%s guild=%s updated=%s skipped=%s",
        interaction.user.id,
        cast(Guild, interaction.guild).id,
        changed,
        skipped,
    )
    return await interaction.response.send_message(
        embed=Embed(
            title="Notifications Configuration",
            description=description,
            color=discord.Color.green(),
        ),
        ephemeral=True,
    )
