"""Logging configuration commands for the Nightcore bot."""

import logging
from typing import Literal, cast

import discord
from discord import app_commands
from discord.embeds import Embed
from discord.interactions import Interaction, InteractionCallbackResponse

from src.nightcore.bot import Nightcore
from src.nightcore.commands.config._groups import logging as logging_group
from src.nightcore.components.embed.error import NoOptionsSuppliedEmbed
from src.nightcore.services.config import open_guild_config
from src.nightcore.utils.config_commands import (
    FieldSpec,
    apply_field_changes,
    format_changes,
    int_id_value,
    list_csv,
    split_changes,
    update_id_list,
)

logger = logging.getLogger(__name__)


@logging_group.command(name="setup", description="Configure logging settings.")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    bans="The channel to log bans.",
    voices="The channel to log voice state changes.",
    members="The channel to log member updates.",
    channels="The channel to log channel updates.",
    roles="The channel to log role updates.",
    messages="The channel to log message updates.",
    moderation="The channel to log moderation actions.",
    tickets="The channel to log ticket updates.",
    reactions="The channel to log reaction updates.",
    private_rooms="The channel to log private room updates.",
    ignoring_channels="The channels to ignore for logging. Type: `id,id,id,...`",  # noqa: E501
)
async def setup_logging(
    interaction: Interaction,
    bans: discord.TextChannel | None = None,
    voices: discord.TextChannel | None = None,
    members: discord.TextChannel | None = None,
    channels: discord.TextChannel | None = None,
    roles: discord.TextChannel | None = None,
    messages: discord.TextChannel | None = None,
    moderation: discord.TextChannel | None = None,
    tickets: discord.TextChannel | None = None,
    reactions: discord.TextChannel | None = None,
    private_rooms: discord.TextChannel | None = None,
    ignoring_channels: str | None = None,
) -> InteractionCallbackResponse:
    """Configure logging settings for the guild."""
    specs: list[FieldSpec | None] = [
        int_id_value("bans_log_channel_id", bans),
        int_id_value("voices_log_channel_id", voices),
        int_id_value("members_log_channel_id", members),
        int_id_value("channels_log_channel_id", channels),
        int_id_value("roles_log_channel_id", roles),
        int_id_value("messages_log_channel_id", messages),
        int_id_value("moderation_log_channel_id", moderation),
        int_id_value("tickets_log_channel_id", tickets),
        int_id_value("reactions_log_channel_id", reactions),
        int_id_value("private_rooms_log_channel_id", private_rooms),
        list_csv("message_log_ignoring_channels_ids", ignoring_channels),
    ]

    specs = [s for s in specs if s is not None]

    if not specs:
        logger.info(
            "config.logging invoked user=%s guild=%s no_options_supplied",
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
        "config.logging invoked user=%s guild=%s updated=%s skipped=%s",
        interaction.user.id,  # type: ignore
        interaction.guild.id,  # type: ignore
        changed,
        skipped,
    )
    return await interaction.response.send_message(
        embed=Embed(
            title="Logging Configuration",
            description=description,
            color=discord.Color.green(),
        ),
        ephemeral=True,
    )


@logging_group.command(name="update_ignoring_channels")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.choices(
    option=[
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Remove", value="remove"),
    ]
)
@app_commands.describe(
    channel="The channel to update",
    option="Whether to add or remove the channel from the ignore list",
)
async def update_ignoring_channels(
    interaction: Interaction,
    channel: discord.TextChannel,
    option: Literal["add", "remove"],
) -> InteractionCallbackResponse:
    """Update the list of channels to ignore for logging."""
    async with open_guild_config(
        cast(Nightcore, interaction.client),
        interaction.guild.id,  # type: ignore
    ) as guild_config:
        new_list, changed, state = update_id_list(
            guild_config.message_log_ignoring_channels_ids,
            channel.id,
            option,
        )
        if changed:
            guild_config.message_log_ignoring_channels_ids = new_list

    if state == "exists":
        desc = f"Channel <@&{channel.id}> already exists in the ignore list."
        color = discord.Color.yellow()
    elif state == "absent":
        desc = f"Channel <#{channel.id}> is not in the ignore list."
        color = discord.Color.red()
    elif state == "added":
        desc = f"Channel <#{channel.id}> added to the ignore list."
        color = discord.Color.blurple()
    else:  # removed
        desc = f"Channel <#{channel.id}> removed from the ignore list."
        color = discord.Color.blurple()

    logger.info(
        "config.logging.update_ignoring_channels user=%s guild=%s option=%s channel=%s",  # noqa: E501
        interaction.user.id,  # type: ignore
        interaction.guild.id,  # type: ignore
        option,
        channel.id,
    )
    return await interaction.response.send_message(
        embed=Embed(
            title="Logging Configuration",
            description=desc,
            color=color,
        ),
        ephemeral=True,
    )
