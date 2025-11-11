"""Subgroup to configure moderation system."""

import logging
from typing import Literal, cast

import discord
from discord import Guild, app_commands
from discord.embeds import Embed
from discord.interactions import Interaction
from sqlalchemy.orm import attributes

from src.infra.db.models.guild import GuildModerationConfig
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import NoOptionsSuppliedEmbed
from src.nightcore.features.config._groups import (
    moderation as moderation_group,
)
from src.nightcore.features.config.utils import fraction_roles_dict_value
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.field_validators import (
    FieldSpec,
    apply_field_changes,
    format_changes,
    int_id_value,
    list_csv,
    split_changes,
    str_value,
    update_id_dict,
    update_id_list,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


@moderation_group.command(
    name="setup", description="Настроить систему модерации."
)  # type: ignore
@app_commands.describe(
    moderation_access_roles="Роли, которые могут получать доступ к функциям модерации",  # noqa: E501
    leadership_access_roles="Роли, которые могут получать доступ к функциям модерации для руководства.",  # noqa: E501
    ban_access_roles="Роли, которые могут получать доступ к бану.",
    ban_request_ping_role="Роль, которую нужно пинговать, когда создается запрос на бан.",  # noqa: E501
    ban_request_channel="Канал, в котором создаются запросы на бан.",
    mute_type="Тип мута, который нужно применить: Timeout | Role",
    mute_role="Роль, которую нужно назначить, когда пользователь замьючен.",
    mpmute_role="Роль, которую нужно назначить, когда пользователь замьючен в торговой площадке.",  # noqa: E501
    vmute_role="Роль, которую нужно назначить, когда пользователь замьючен в голосовом канале.",  # noqa: E501
    leaders_access_rr_roles="Роли лидеров с доступом к команде /rr.",
    fraction_roles_access="Роли, с доступом к команде `/fraction_role`, формат: role_id, roleaccessid_roleaccessids_... | ...",  # noqa: E501
)
@app_commands.choices(
    mute_type=[
        app_commands.Choice(name="Timeout", value="timeout"),
        app_commands.Choice(name="Role", value="role"),
    ]
)
@check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)
async def setup_moderation(
    interaction: Interaction,
    moderation_access_roles: str | None = None,  #
    leadership_access_roles: str | None = None,  #
    ban_access_roles: str | None = None,  #
    ban_request_ping_role: discord.Role | None = None,  #
    ban_request_channel: discord.TextChannel | None = None,  #
    mute_type: Literal["timeout", "role"] | None = None,  #
    mute_role: discord.Role | None = None,  #
    mpmute_role: discord.Role | None = None,  #
    vmute_role: discord.Role | None = None,  #
    leaders_access_rr_roles: str | None = None,  #
    fraction_roles_access: str | None = None,  #
):
    """Configure moderation settings."""

    specs: list[FieldSpec | None] = [
        int_id_value("ban_request_ping_role_id", ban_request_ping_role),
        int_id_value("send_ban_request_channel_id", ban_request_channel),
        int_id_value("mute_role_id", mute_role),
        int_id_value("mpmute_role_id", mpmute_role),
        int_id_value("vmute_role_id", vmute_role),
        list_csv("moderation_access_roles_ids", moderation_access_roles),
        list_csv("leadership_access_roles_ids", leadership_access_roles),
        list_csv("ban_access_roles_ids", ban_access_roles),
        list_csv("leader_access_rr_roles_ids", leaders_access_rr_roles),
        fraction_roles_dict_value(
            "fraction_roles_access_roles_ids", fraction_roles_access
        ),
        str_value("mute_type", mute_type),
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
        config_type=GuildModerationConfig,
        _create=True,
    ) as (guild_config, _):
        changes = apply_field_changes(guild_config, specs)  # type: ignore

    changed, skipped = split_changes(changes)
    description = format_changes(changed, skipped)

    await interaction.response.send_message(
        embed=Embed(
            title="Настройка модерации",
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


@moderation_group.command(name="update_moderation_access")  # type: ignore
@app_commands.choices(
    option=[
        app_commands.Choice(name="Добавить", value="add"),
        app_commands.Choice(name="Удалить", value="remove"),
    ]
)
@app_commands.describe(
    role="Роль для обновления",
    option="Добавить или удалить роль из списка ролей с доступом к модерации",
)
@check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)
async def update_moderation_access(
    interaction: Interaction,
    role: discord.Role,
    option: Literal["add", "remove"],
):
    """Update the list of roles with moderation access."""

    async with specified_guild_config(
        cast(Nightcore, interaction.client),
        cast(Guild, interaction.guild).id,
        config_type=GuildModerationConfig,
    ) as (guild_config, _):
        new_list, changed, state = update_id_list(
            guild_config.moderation_access_roles_ids,
            role.id,
            option,
        )
        if changed:
            guild_config.moderation_access_roles_ids = new_list

    if state == "exists":
        desc = f"Роль <@&{role.id}> уже в списке ролей с доступом к модерации."
        color = discord.Color.yellow()
    elif state == "absent":
        desc = f"Роль <@&{role.id}> не в списке ролей с доступом к модерации."
        color = discord.Color.red()
    elif state == "added":
        desc = f"Роль <@&{role.id}> добавлена в список ролей с доступом к модерации."  # noqa: E501
        color = discord.Color.blurple()
    else:
        desc = f"Роль <@&{role.id}> удалена из списка ролей с доступом к модерации."  # noqa: E501
        color = discord.Color.blurple()

    await interaction.response.send_message(
        embed=Embed(
            title="Настройка модерации",
            description=desc,
            color=color,
        ),
        ephemeral=True,
    )

    logger.info(
        "[command] - update_moderation_access user=%s guild=%s option=%s role=%s",  # noqa: E501
        interaction.user.id,
        cast(Guild, interaction.guild).id,
        option,
        role.id,
    )


@moderation_group.command(name="update_ban_access")  # type: ignore
@app_commands.choices(
    option=[
        app_commands.Choice(name="Добавить", value="add"),
        app_commands.Choice(name="Удалить", value="remove"),
    ]
)
@app_commands.describe(
    role="Роль для обновления",
    option="Добавить или удалить роль из списка ролей с доступом к бану",
)
@check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)
async def update_ban_access(
    interaction: Interaction,
    role: discord.Role,
    option: Literal["add", "remove"],
):
    """Update the list of roles with ban access."""
    async with specified_guild_config(
        cast(Nightcore, interaction.client),
        cast(Guild, interaction.guild).id,
        config_type=GuildModerationConfig,
    ) as (guild_config, _):
        new_list, changed, state = update_id_list(
            guild_config.ban_access_roles_ids,
            role.id,
            option,
        )
        if changed:
            guild_config.ban_access_roles_ids = new_list

    if state == "exists":
        desc = f"Роль <@&{role.id}> уже в списке ролей с доступом к бану."
        color = discord.Color.yellow()
    elif state == "absent":
        desc = f"Роль <@&{role.id}> не в списке ролей с доступом к бану."
        color = discord.Color.red()
    elif state == "added":
        desc = (
            f"Роль <@&{role.id}> добавлена в список ролей с доступом к бану."
        )
        color = discord.Color.blurple()
    else:  # removed
        desc = f"Роль <@&{role.id}> удалена из списка ролей с доступом к бану."
        color = discord.Color.blurple()

    await interaction.response.send_message(
        embed=Embed(
            title="Настройка модерации",
            description=desc,
            color=color,
        ),
        ephemeral=True,
    )

    logger.info(
        "[command] - update_ban_access user=%s guild=%s option=%s role=%s",
        interaction.user.id,
        cast(Guild, interaction.guild).id,
        option,
        role.id,
    )


@moderation_group.command(name="update_rr_access")  # type: ignore
@app_commands.choices(
    option=[
        app_commands.Choice(name="Добавить", value="add"),
        app_commands.Choice(name="Удалить", value="remove"),
    ]
)
@check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)
@app_commands.describe(
    role="Роль для обновления",
    option="Добавить или удалить роль из списка ролей с доступом к rr",
)
async def update_rr_access(
    interaction: Interaction,
    role: discord.Role,
    option: Literal["add", "remove"],
):
    """Update the list of leaders roles with `rr` access."""
    async with specified_guild_config(
        cast(Nightcore, interaction.client),
        cast(Guild, interaction.guild).id,
        config_type=GuildModerationConfig,
        _create=True,
    ) as (guild_config, _):
        new_list, changed, state = update_id_list(
            guild_config.leader_access_rr_roles_ids,
            role.id,
            option,
        )

        if changed:
            guild_config.leader_access_rr_roles_ids = new_list

    if state == "exists":
        desc = f"Роль <@&{role.id}> уже в списке ролей с доступом к rr."
        color = discord.Color.yellow()
    elif state == "absent":
        desc = f"Роль <@&{role.id}> не в списке ролей с доступом к rr."
        color = discord.Color.red()
    elif state == "added":
        desc = f"Роль <@&{role.id}> добавлена в список ролей с доступом к rr."
        color = discord.Color.blurple()
    else:  # removed
        desc = f"Роль <@&{role.id}> удалена из списка ролей с доступом к rr."
        color = discord.Color.blurple()

    await interaction.response.send_message(
        embed=Embed(
            title="Настройка модерации",
            description=desc,
            color=color,
        ),
        ephemeral=True,
    )

    logger.info(
        "[command] - update_rr_access user=%s guild=%s option=%s role=%s",
        interaction.user.id,
        cast(Guild, interaction.guild).id,
        option,
        role.id,
    )


@moderation_group.command(name="update_fraction_role_access")  # type: ignore
@app_commands.choices(
    option=[
        app_commands.Choice(name="Добавить", value="add"),
        app_commands.Choice(name="Удалить", value="remove"),
    ]
)
@app_commands.describe(
    access_role="Роль которой выдается доступ к fraction_role",
    fraction_role="Роль для которой выдается доступ. Пример: role=лидер фбр, fraction_role=инспектор фбр",  # noqa: E501
    option="Добавить или удалить роль из списка ролей с доступом",
)
@check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)
async def update_fraction_role_access(
    interaction: Interaction,
    access_role: discord.Role,
    fraction_role: discord.Role,
    option: Literal["add", "remove"],
):
    """Update the list of roles with `fraction_role` access."""

    async with specified_guild_config(
        cast(Nightcore, interaction.client),
        cast(Guild, interaction.guild).id,
        config_type=GuildModerationConfig,
        _create=True,
    ) as (guild_config, _):
        new_dict, changed, state = update_id_dict(
            guild_config.fraction_roles_access_roles_ids,
            str(fraction_role.id),
            access_role.id,
            option,
        )

        logger.info("New dict of rr access roles: %s", new_dict)
        logger.info("Changes made to rr access roles: %s", changed)
        logger.info("State of rr access roles update: %s", state)

        if changed:
            guild_config.fraction_roles_access_roles_ids = new_dict
            attributes.flag_modified(
                guild_config, "fraction_roles_access_roles_ids"
            )

    if state == "exists":
        desc = f"Роль <@&{access_role.id}> уже в списке ролей с доступом к {fraction_role.mention}."  # noqa: E501
        color = discord.Color.yellow()
    elif state == "absent":
        desc = f"Роль <@&{access_role.id}> не в списке ролей с доступом к {fraction_role.mention}."  # noqa: E501
        color = discord.Color.red()
    elif state == "added":
        desc = f"Роль <@&{access_role.id}> добавлена в список ролей с доступом к {fraction_role.mention}."  # noqa: E501
        color = discord.Color.blurple()
    else:
        desc = f"Роль <@&{access_role.id}> удалена из списка ролей с доступом к {fraction_role.mention}."  # noqa: E501
        color = discord.Color.blurple()

    await interaction.response.send_message(
        embed=Embed(
            title="Настройка модерации",
            description=desc,
            color=color,
        ),
        ephemeral=True,
    )

    logger.info(
        "[command] - update_fraction_role_access user=%s guild=%s option=%s access_role=%s fraction_role=%s",  # noqa: E501
        interaction.user.id,
        cast(Guild, interaction.guild).id,
        option,
        access_role.id,
        fraction_role.id,
    )


@moderation_group.command(name="update_leardership_access")  # type: ignore
@app_commands.choices(
    option=[
        app_commands.Choice(name="Добавить", value="add"),
        app_commands.Choice(name="Удалить", value="remove"),
    ]
)
@app_commands.describe(
    role="Роль для обновления",
    option="Добавить или удалить роль из списка ролей с доступом к модерации для руководства.",  # noqa: E501
)
@check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)
async def update_leadership_access(
    interaction: Interaction,
    role: discord.Role,
    option: Literal["add", "remove"],
):
    """Update the list of roles with leadership moderation access."""
    async with specified_guild_config(
        cast(Nightcore, interaction.client),
        cast(Guild, interaction.guild).id,
        config_type=GuildModerationConfig,
        _create=True,
    ) as (guild_config, _):
        new_list, changed, state = update_id_list(
            guild_config.leadership_access_roles_ids,
            role.id,
            option,
        )
        if changed:
            guild_config.leadership_access_roles_ids = new_list

    if state == "exists":
        desc = f"Роль <@&{role.id}> уже в списке ролей с доступом к модерации для руководства."  # noqa: E501
        color = discord.Color.yellow()
    elif state == "absent":
        desc = f"Роль <@&{role.id}> не в списке ролей с доступом к модерации для руководства."  # noqa: E501
        color = discord.Color.red()
    elif state == "added":
        desc = f"Роль <@&{role.id}> добавлена в список ролей с доступом к модерации для руководства."  # noqa: E501
        color = discord.Color.blurple()
    else:  # removed
        desc = f"Роль <@&{role.id}> удалена из списка ролей с доступом к модерации для руководства."  # noqa: E501
        color = discord.Color.blurple()

    await interaction.response.send_message(
        embed=Embed(
            title="Настройка модерации",
            description=desc,
            color=color,
        ),
        ephemeral=True,
    )

    logger.info(
        "[command] - update_leadership_access user=%s guild=%s option=%s role=%s",  # noqa: E501
        interaction.user.id,
        cast(Guild, interaction.guild).id,
        option,
        role.id,
    )
