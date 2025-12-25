"""Subgroup to configure levels settings."""

import logging
from typing import Literal, cast

import discord
from discord import Guild, app_commands
from discord.embeds import Embed
from discord.interactions import Interaction

from src.infra.db.models.guild import GuildLevelsConfig
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import NoOptionsSuppliedEmbed
from src.nightcore.features.config._groups import levels as levels_group
from src.nightcore.features.config.utils import (
    bonus_roles_dict_value,
    level_roles_dict_value,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.field_validators import (
    FieldSpec,
    apply_field_changes,
    float_value,
    format_changes,
    int_id_value,
    split_changes,
    str_value,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


@levels_group.command(name="setup", description="Настроить систему уровней.")  # type: ignore
@app_commands.describe(
    count_messages_channel="Канал для подсчета сообщений для уровней.",
    count_messages_type="Тип подсчета сообщений для уровней: Все каналы | Только указанный",  # noqa: E501
    level_notify_channel="Канал для уведомлений о повышении уровня.",
    exp_multiplier="Множитель опыта для уровней.",
    coins_multiplier="Множитель монет для уровней.",
    battlepass_multiplier="Множитель опыта для боевого пропуска.",
    roles_with_bonus="Роли, которые получают бонусные очки опыта. Формат: role_id, multiplier | ...",  # noqa: E501
    roles_per_level="Роли, назначаемые на каждом уровне. Формат: level, role_id | level, role_id | ...",  # noqa: E501
)
@app_commands.choices(
    count_messages_type=[
        app_commands.Choice(name="Все каналы", value="all"),
        app_commands.Choice(name="Только указанный", value="channel_only"),
    ]
)
@check_required_permissions(PermissionsFlagEnum.LEVELS_CONFIG_ACCESS)
async def setup(
    interaction: Interaction,
    count_messages_channel: discord.TextChannel | None = None,
    count_messages_type: Literal["all", "channel_only"] | None = None,
    level_notify_channel: discord.TextChannel | None = None,
    exp_multiplier: int | None = None,
    coins_multiplier: int | None = None,
    battlepass_multiplier: int | None = None,
    roles_with_bonus: str | None = None,
    roles_per_level: str | None = None,
):
    """Configure levels settings for the guild."""
    specs: list[FieldSpec | None] = [
        int_id_value("count_messages_channel_id", count_messages_channel),
        str_value("count_messages_type", count_messages_type),
        int_id_value("level_notify_channel_id", level_notify_channel),
        int_id_value("base_exp_multiplier", exp_multiplier),
        int_id_value("base_coins_multiplier", coins_multiplier),
        int_id_value("base_battlepass_multiplier", battlepass_multiplier),
        bonus_roles_dict_value("bonus_access_roles_ids", roles_with_bonus),
        level_roles_dict_value("level_roles", roles_per_level),
    ]

    specs = [s for s in specs if s is not None]

    if not specs:
        logger.info(
            "[command] - invoked user=%s guild=%s no_options_supplied",
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
        _create=True,
    ) as (guild_config, _):
        changes = apply_field_changes(guild_config, specs)  # type: ignore

    changed, skipped = split_changes(changes)
    description = format_changes(changed, skipped)

    await interaction.response.send_message(
        embed=Embed(
            title="Настройка системы уровней",
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
