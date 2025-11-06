"""Subgroup to configure infomaker settings."""

import logging
from typing import Literal, cast

import discord
from discord import Guild, app_commands
from discord.embeds import Embed
from discord.interactions import Interaction

from src.infra.db.models.guild import GuildInfomakerConfig
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import NoOptionsSuppliedEmbed
from src.nightcore.features.config._groups import (
    infomaker as infomaker_group,
)
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

logger = logging.getLogger(__name__)


@infomaker_group.command(
    name="setup", description="Настроить логирование для инфомейкера."
)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    admins_roles="Роли администраторов, которые будут логироваться. Формат: role_id,role_id,role_id,...",  # noqa: E501
    leaders_roles="Роли лидеров, которые будут логироваться. Формат: role_id,role_id,role_id,...",  # noqa: E501
    admins_logging_channel="Канал, в который будут отправляться логи административных ролей.",  # noqa: E501
    leaders_logging_channel="Канал, в который будут отправляться логи лидерских ролей.",  # noqa: E501
)
async def setup_infomaker(
    interaction: Interaction,
    admins_roles: str | None = None,
    leaders_roles: str | None = None,
    admins_logging_channel: discord.TextChannel | None = None,
    leaders_logging_channel: discord.TextChannel | None = None,
):
    """Configure infomaker settings."""

    specs: list[FieldSpec | None] = [
        list_csv("admins_roles_ids", admins_roles),
        list_csv("leaders_roles_ids", leaders_roles),
        int_id_value(
            "admins_roles_logging_channel_id", admins_logging_channel
        ),
        int_id_value(
            "leaders_roles_logging_channel_id", leaders_logging_channel
        ),
    ]

    specs = [s for s in specs if s is not None]

    if not specs:
        logger.info(
            "[command] - invoked user=%s guild=%s no_options_supplied",
            interaction.user.id,
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
        config_type=GuildInfomakerConfig,
        _create=True,
    ) as (guild_config, _):
        changes = apply_field_changes(guild_config, specs)  # type: ignore

    changed, skipped = split_changes(changes)
    description = format_changes(changed, skipped)

    await interaction.response.send_message(
        embed=Embed(
            title="Настройка логирования для инфомейкера",
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


@infomaker_group.command(
    name="update_admins_roles",
    description="Обновить логируемые роли администраторов.",
)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.choices(
    option=[
        app_commands.Choice(name="Добавить", value="add"),
        app_commands.Choice(name="Удалить", value="remove"),
    ]
)
@app_commands.describe(
    role="Роль для обновления",
    option="Добавить или удалить роль из списка логируемых ролей",
)
async def update_admins_roles(
    interaction: Interaction,
    role: discord.Role,
    option: Literal["add", "remove"],
):
    """Update the list of admin infomaker roles."""
    async with specified_guild_config(
        cast(Nightcore, interaction.client),
        cast(Guild, interaction.guild).id,
        config_type=GuildInfomakerConfig,
    ) as (guild_config, _):
        new_list, changed, state = update_id_list(
            guild_config.admins_roles_ids,
            role.id,
            option,
        )
        if changed:
            guild_config.admins_roles_ids = new_list

    if state == "exists":
        desc = f"Роль <@&{role.id}> уже в списке логируемых ролей администраторов."  # noqa: E501
        color = discord.Color.yellow()
    elif state == "absent":
        desc = (
            f"Роль <@&{role.id}> не в списке логируемых ролей администраторов."
        )
        color = discord.Color.red()
    elif state == "added":
        desc = f"Роль <@&{role.id}> добавлена в список логируемых ролей администраторов."  # noqa: E501
        color = discord.Color.blurple()
    else:
        desc = f"Роль <@&{role.id}> удалена из списка логируемых ролей администраторов."  # noqa: E501
        color = discord.Color.blurple()

    await interaction.response.send_message(
        embed=Embed(
            title="Настройка логирования для инфомейкера",
            description=desc,
            color=color,
        ),
        ephemeral=True,
    )

    logger.info(
        "[command] - update_admins_roles user=%s guild=%s option=%s role=%s",
        interaction.user.id,
        cast(Guild, interaction.guild).id,
        option,
        role.id,
    )


@infomaker_group.command(
    name="update_leaders_roles",
    description="Обновить логируемые роли лидеров.",
)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.choices(
    option=[
        app_commands.Choice(name="Добавить", value="add"),
        app_commands.Choice(name="Удалить", value="remove"),
    ]
)
@app_commands.describe(
    role="Роль для обновления",
    option="Добавить или удалить роль из списка логируемых ролей",
)
async def update_leaders_roles(
    interaction: Interaction,
    role: discord.Role,
    option: Literal["add", "remove"],
):
    """Update the list of leader infomaker roles."""
    async with specified_guild_config(
        cast(Nightcore, interaction.client),
        cast(Guild, interaction.guild).id,
        config_type=GuildInfomakerConfig,
    ) as (guild_config, _):
        new_list, changed, state = update_id_list(
            guild_config.leaders_roles_ids,
            role.id,
            option,
        )
        if changed:
            guild_config.leaders_roles_ids = new_list

    if state == "exists":
        desc = f"Роль <@&{role.id}> уже в списке логируемых ролей лидеров."
        color = discord.Color.yellow()
    elif state == "absent":
        desc = f"Роль <@&{role.id}> не в списке логируемых ролей лидеров."
        color = discord.Color.red()
    elif state == "added":
        desc = (
            f"Роль <@&{role.id}> добавлена в список логируемых ролей лидеров."
        )
        color = discord.Color.blurple()
    else:
        desc = (
            f"Роль <@&{role.id}> удалена из списка логируемых ролей лидеров."
        )
        color = discord.Color.blurple()

    await interaction.response.send_message(
        embed=Embed(
            title="Настройка логирования для инфомейкера",
            description=desc,
            color=color,
        ),
        ephemeral=True,
    )

    logger.info(
        "[command] - update_leaders_roles user=%s guild=%s option=%s role=%s",
        interaction.user.id,
        cast(Guild, interaction.guild).id,
        option,
        role.id,
    )
