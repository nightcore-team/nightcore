"""Levels configuration commands for the Nightcore bot."""

import logging
from typing import cast

import discord
from discord import Guild, app_commands
from discord.embeds import Embed
from discord.interactions import Interaction, InteractionCallbackResponse

from src.infra.db.models.guild import GuildLevelsConfig
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import NoOptionsSuppliedEmbed
from src.nightcore.features.config._groups import levels as levels_group
from src.nightcore.features.config.utils import level_roles_dict_value
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.field_validators import (
    FieldSpec,
    apply_field_changes,
    float_value,
    format_changes,
    int_id_value,
    list_csv,
    split_changes,
)

logger = logging.getLogger(__name__)


@levels_group.command(name="setup", description="Configure levels settings.")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    count_messages_channel="Channel to count messages for levels.",
    level_notify_channel="Channel for level-up notifications.",
    exp_multiplier="Experience points multiplier for levels.",
    coins_multiplier="Coins multiplier for levels.",
    roles_with_bonus="Roles that receive bonus experience points.",
    roles_per_level="Roles assigned at each level (format: level1:role1|level2:role2|...).",  # noqa: E501
)
async def setup(
    interaction: Interaction,
    count_messages_channel: discord.TextChannel | None = None,
    level_notify_channel: discord.TextChannel | None = None,
    exp_multiplier: float | None = None,
    coins_multiplier: float | None = None,
    roles_with_bonus: str | None = None,
    roles_per_level: str | None = None,
) -> InteractionCallbackResponse:
    """Configure levels settings for the guild."""
    specs: list[FieldSpec | None] = [
        int_id_value("count_messages_channel_id", count_messages_channel),
        int_id_value("level_notify_channel_id", level_notify_channel),
        float_value("base_exp_multiplier", exp_multiplier),
        float_value("base_coins_multiplier", coins_multiplier),
        list_csv("bonus_access_roles_ids", roles_with_bonus),
        level_roles_dict_value("level_roles", roles_per_level),
    ]

    specs = [s for s in specs if s is not None]

    if not specs:
        logger.info(
            "config.levels.setup invoked user=%s guild=%s no_options_supplied",
            interaction.user.id,
            cast(Guild, interaction.guild).id,
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
        config_type=GuildLevelsConfig,
    ) as guild_config:
        changes = apply_field_changes(guild_config, specs)  # type: ignore

    changed, skipped = split_changes(changes)
    description = format_changes(changed, skipped)

    logger.info(
        "config.levels.setup invoked user=%s guild=%s updated=%s skipped=%s",
        interaction.user.id,
        cast(Guild, interaction.guild).id,
        changed,
        skipped,
    )
    return await interaction.response.send_message(
        embed=Embed(
            title="Levels Configuration",
            description=description,
            color=discord.Color.green(),
        ),
        ephemeral=True,
    )
