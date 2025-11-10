"""Subgroup to configure clans settings."""

import logging
from typing import Literal, cast

import discord
from discord import Guild, app_commands
from discord.embeds import Embed
from discord.interactions import Interaction

from src.infra.db.models.guild import GuildClansConfig
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import NoOptionsSuppliedEmbed
from src.nightcore.features.config._groups import clans as clans_group
from src.nightcore.features.config.utils import shop_items_dict_value
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.field_validators import (
    FieldSpec,
    apply_field_changes,
    format_changes,
    int_id_value,
    list_csv,
    split_changes,
    update_id_list,
)

from src.nightcore.utils.permissions import check_required_permissions, PermissionsFlagEnum

logger = logging.getLogger(__name__)


@clans_group.command(name="setup", description="Настроить систему кланов.") # type: ignore
@app_commands.describe(
    shop_threads_channel="Канал, под которым создаются ветки с покупками.",
    shop_buy_ping_roles="Роли для упоминания при покупке в магазине. Формат: role_id, role_id, ...",  # noqa: E501
    shop_items="Товары, доступные в магазине. Формат: item_name, price | item_name, price | ...",  # noqa: E501
    reputation_per_payday="Количество репутации, выдаваемой в пейдэй.",
    payday_channel="Канал для объявлений о дне зарплаты.",
    base_exp_multiplier="Базовый множитель опыта, выдаваемого за сообщение.",
    improvements_costs="Стоимость улучшений клана (Всего их 3). Формат: cost,cost,cost",  # noqa: E501
)
@check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)
async def setup(
    interaction: Interaction,
    shop_threads_channel: discord.TextChannel | None = None,
    shop_buy_ping_roles: str | None = None,
    shop_items: str | None = None,
    reputation_per_payday: int | None = None,
    base_exp_multiplier: int | None = None,
    payday_channel: discord.TextChannel | None = None,
    improvements_costs: str | None = None,
):
    """Configure clans settings."""

    specs: list[FieldSpec | None] = [
        int_id_value("clan_shop_channel_id", shop_threads_channel),
        list_csv("clan_buy_ping_roles_ids", shop_buy_ping_roles),
        shop_items_dict_value("clan_shop_items", shop_items),
        int_id_value("clan_reputation_per_payday", reputation_per_payday),
        int_id_value("base_exp_multiplier", base_exp_multiplier),
        int_id_value("clan_payday_channel_id", payday_channel),
        list_csv("clan_improvements", improvements_costs, _len=3),
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
        config_type=GuildClansConfig,
        _create=True,
    ) as (guild_config, _):
        changes = apply_field_changes(guild_config, specs)  # type: ignore

    changed, skipped = split_changes(changes)
    description = format_changes(changed, skipped)

    await interaction.response.send_message(
        embed=Embed(
            title="Настройка системы кланов",
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


@clans_group.command(
    name="update_clans_access",
    description="Обновить список ролей с доступом к кланам.",
) # type: ignore
@app_commands.choices(
    option=[
        app_commands.Choice(name="Добавить", value="add"),
        app_commands.Choice(name="Удалить", value="remove"),
    ]
)
@app_commands.describe(
    role="Роль для обновления",
    option="Добавить или удалить роль из списка доступа к кланам.",
)
@check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)
async def update_clans_access(
    interaction: Interaction,
    role: discord.Role,
    option: Literal["add", "remove"],
):
    """Update the list of roles with `clans` access."""
    async with specified_guild_config(
        cast(Nightcore, interaction.client),
        cast(Guild, interaction.guild).id,
        config_type=GuildClansConfig,
        _create=True,
    ) as (guild_config, _):
        new_list, changed, state = update_id_list(
            guild_config.clans_access_roles_ids,
            role.id,
            option,
        )
        if changed:
            guild_config.clans_access_roles_ids = new_list

    if state == "exists":
        desc = f"Роль <@&{role.id}> уже в списке доступа к кланам."
        color = discord.Color.yellow()
    elif state == "absent":
        desc = f"Роль <@&{role.id}> не в списке доступа к кланам."
        color = discord.Color.red()
    elif state == "added":
        desc = f"Роль <@&{role.id}> добавлена в список доступа к кланам."
        color = discord.Color.blurple()
    else:  # removed
        desc = f"Роль <@&{role.id}> удалена из списка доступа к кланам."
        color = discord.Color.blurple()

    await interaction.response.send_message(
        embed=Embed(
            title="Настройка системы кланов",
            description=desc,
            color=color,
        ),
        ephemeral=True,
    )

    logger.info(
        "[command] - invoked user=%s guild=%s option=%s role=%s",
        interaction.user.id,
        cast(Guild, interaction.guild).id,
        option,
        role.id,
    )
