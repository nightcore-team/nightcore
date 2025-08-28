"""Private Channels configuration commands for the Nightcore bot."""

import logging
from typing import cast

import discord
from discord import Guild, app_commands
from discord.embeds import Embed
from discord.interactions import Interaction

from src.infra.db.models.guild import GuildPrivateChannelsConfig
from src.nightcore.bot import Nightcore
from src.nightcore.components import NoOptionsSuppliedEmbed
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
    name="private_channels",
    description="Configure private channels settings.",
)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    create_private_channel="The channel to create for private rooms."
)
async def private_channels(
    interaction: Interaction,
    create_private_channel: discord.VoiceChannel | None = None,
):
    """Configure private channels settings."""
    specs: list[FieldSpec | None] = [
        int_id_value("private_rooms_create_channel_id", create_private_channel)
    ]

    specs = [s for s in specs if s is not None]

    if not specs:
        logger.info(
            "[command] - invoked user=%s guild=%s no_options_supplied",
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
        config_type=GuildPrivateChannelsConfig,
    ) as guild_config:
        changes = apply_field_changes(guild_config, specs)  # type: ignore

    changed, skipped = split_changes(changes)
    description = format_changes(changed, skipped)

    await interaction.response.send_message(
        embed=Embed(
            title="Private Channels Configuration",
            description=description,
            color=discord.Color.green(),
        ),
        ephemeral=True,
    )

    logger.info(
        "[command] - invoked user=%s guild=%s updated=%s skipped=%s",
        interaction.user.id,
        cast(Guild, interaction.guild).id,
        changed,
        skipped,
    )
