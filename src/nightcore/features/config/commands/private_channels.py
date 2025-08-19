"""Private Channels configuration commands for the Nightcore bot."""

import logging
from typing import cast

import discord
from discord import Guild, InteractionCallbackResponse, app_commands
from discord.embeds import Embed
from discord.interactions import Interaction

from src.nightcore.bot import Nightcore
from src.nightcore.components.embed.error import NoOptionsSuppliedEmbed
from src.nightcore.features.config._groups import config as main_config_group
from src.nightcore.services.config import open_guild_config
from src.nightcore.utils.config_commands import (
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
) -> InteractionCallbackResponse:
    """Configure private channels settings."""
    specs: list[FieldSpec | None] = [
        int_id_value("private_rooms_create_channel_id", create_private_channel)
    ]

    specs = [s for s in specs if s is not None]

    if not specs:
        logger.info(
            "config.private_channels invoked user=%s guild=%s no_options_supplied",  # noqa: E501
            interaction.user.id,  # type: ignore
            interaction.guild.id,  # type: ignore
        )
        return await interaction.response.send_message(
            embed=NoOptionsSuppliedEmbed(),
            ephemeral=True,
        )

    async with open_guild_config(
        cast(Nightcore, interaction.client),
        interaction.guild.id,  # type: ignore
    ) as guild_config:
        changes = apply_field_changes(guild_config, specs)  # type: ignore

    changed, skipped = split_changes(changes)
    description = format_changes(changed, skipped)

    logger.info(
        "config.private_channels invoked user=%s guild=%s updated=%s skipped=%s",  # noqa: E501
        interaction.user.id,
        cast(Guild, interaction.guild).id,
        changed,
        skipped,
    )
    return await interaction.response.send_message(
        embed=Embed(
            title="Private Channels Configuration",
            description=description,
            color=discord.Color.green(),
        ),
        ephemeral=True,
    )
