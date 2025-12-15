"""Subcommand to configure moderstats settings."""

import logging
from typing import cast

import discord
from discord import Guild, app_commands
from discord.embeds import Embed
from discord.interactions import Interaction

from src.infra.db.models.guild import GuildModerationConfig
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import NoOptionsSuppliedEmbed
from src.nightcore.features.config._groups import config as main_config_group
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.field_validators import (
    FieldSpec,
    apply_field_changes,
    float_value,
    format_changes,
    int_id_value,
    split_changes,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


@main_config_group.command(
    name="moderstats", description="Настроить систему статистики модерации"
)  # type: ignore
@check_required_permissions(PermissionsFlagEnum.MODERATION_CONFIG_ACCESS)
@app_commands.describe(
    mute="Mute score",  #
    ban="Ban score",  #
    kick="Kick score",  #
    ticket="Ticket score",  #
    vmute="Voice mute score",  #
    mpmute="Member mute score",  #
    ticket_ban="Ticket ban score",  #
    role_request="Role request score",  #
    role_remove="Role remove score",  #
    message="Message score",  #
    role="Роль для отслеживания статистики модерации",  #
    channel="Канал для подсчета сообщений модераторов",  #
)
async def moderstats(
    interaction: Interaction,
    mute: float | None = None,
    ban: float | None = None,
    kick: float | None = None,
    ticket: float | None = None,
    vmute: float | None = None,
    mpmute: float | None = None,
    ticket_ban: float | None = None,
    role_request: float | None = None,
    role_remove: float | None = None,
    message: float | None = None,
    role: discord.Role | None = None,
    channel: discord.TextChannel | None = None,
):
    """Configure moderation stats settings."""

    specs: list[FieldSpec | None] = [
        float_value("mute_score", mute),
        float_value("ban_score", ban),
        float_value("kick_score", kick),
        float_value("ticket_score", ticket),
        float_value("vmute_score", vmute),
        float_value("mpmute_score", mpmute),
        float_value("ticket_ban_score", ticket_ban),
        float_value("role_request_score", role_request),
        float_value("role_remove_score", role_remove),
        float_value("message_score", message),
        int_id_value("trackable_moderation_role_id", role),
        int_id_value("count_moderator_messages_channel_id", channel),
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
        config_type=GuildModerationConfig,
        _create=True,
    ) as (guild_config, _):
        changes = apply_field_changes(guild_config, specs)  # type: ignore

    changed, skipped = split_changes(changes)
    description = format_changes(changed, skipped)

    await interaction.response.send_message(
        embed=Embed(
            title="Настройка системы статистики модерации",
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
