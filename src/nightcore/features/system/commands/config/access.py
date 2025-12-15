"""Subcommands to setup access to each system."""

import logging
from typing import Literal, cast

import discord
from discord import Guild, app_commands
from discord.embeds import Embed
from discord.interactions import Interaction

from src.infra.db.models._enums import MetaConfigAccessTypeEnum
from src.infra.db.models.meta import GuildMetaConfig
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import NoOptionsSuppliedEmbed
from src.nightcore.features.system._groups import config as config_system_group
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.field_validators import (
    FieldSpec,
    apply_field_changes,
    format_changes,
    list_csv,
    split_changes,
    update_id_list,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


@config_system_group.command(
    name="setup_access", description="Настроить доступ к указанной системе."
)  # type: ignore
@app_commands.describe(
    other="Список ролей с доступом к основной конфигурации. Формат: role_id,role_id,...",  # noqa: E501
    clans="Список ролей с доступом к системе кланов. Формат: role_id,role_id,...",  # noqa: E501
    economy="Список ролей с доступом к системе экономики. Формат: role_id,role_id,...",  # noqa: E501
    levels="Список ролей с доступом к системе уровней. Формат: role_id,role_id,...",  # noqa: E501
    logging="Список ролей с доступом к системе логов. Формат: role_id,role_id,...",  # noqa: E501
    moderation="Список ролей с доступом к системе модерации. Формат: role_id,role_id,...",  # noqa: E501
    notifications="Список ролей с доступом к системе уведомлений. Формат: role_id,role_id,...",  # noqa: E501
    private_channels="Список ролей с доступом к системе приватных каналов. Формат: role_id,role_id,...",  # noqa: E501
    tickets="Список ролей с доступом к системе тикетов. Формат: role_id,role_id,...",  # noqa: E501
    infomaker="Список ролей с доступом к системе инфомейкера. Формат: role_id,role_id,...",  # noqa: E501
)
@check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)
async def setup_access(
    interaction: Interaction,
    other: str | None = None,
    clans: str | None = None,
    economy: str | None = None,
    levels: str | None = None,
    logging: str | None = None,
    moderation: str | None = None,
    notifications: str | None = None,
    private_channels: str | None = None,
    tickets: str | None = None,
    infomaker: str | None = None,
):
    """Configure system access settings."""

    specs: list[FieldSpec | None] = [
        list_csv("other_config_access_roles_ids", other),
        list_csv("clans_config_access_roles_ids", clans),
        list_csv("economy_config_access_roles_ids", economy),
        list_csv("levels_config_access_roles_ids", levels),
        list_csv("logging_config_access_roles_ids", logging),
        list_csv("moderation_config_access_roles_ids", moderation),
        list_csv("notifications_config_access_roles_ids", notifications),
        list_csv("private_channels_config_access_roles_ids", private_channels),
        list_csv("tickets_config_access_roles_ids", tickets),
        list_csv("infomaker_config_access_roles_ids", infomaker),
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
        config_type=GuildMetaConfig,
        _create=True,
    ) as (guild_config, _):  # type: ignore
        try:
            changes = apply_field_changes(guild_config, specs)  # type: ignore
        except Exception as e:
            logger.exception(
                "[command/system/config/setup_access] Failed to apply field changes: %s",  # noqa: E501
                e,
            )
            return await interaction.response.send_message(
                embed=Embed(
                    title="Ошибка настройки доступа к системе",
                    description=f"{e}",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )

    changed, skipped = split_changes(changes)
    description = format_changes(changed, skipped)

    await interaction.response.send_message(
        embed=Embed(
            title="Настройка доступа к системе",
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


@config_system_group.command(
    name="update_access",
    description="Обновить список ролей с доступом к указанной системе",
)  # type: ignore
@app_commands.choices(
    system=[
        app_commands.Choice(name="Все", value="all"),
        *[
            app_commands.Choice(name=name, value=value)
            for name, value in MetaConfigAccessTypeEnum.choices()
        ],
    ]
)
@app_commands.describe(
    system="Система для обновления доступа (или 'all' для всех систем)",
    role="Роль для обновления",
    option="Добавить или удалить роль из списка доступа",
)
@check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)
async def update_config_access(
    interaction: Interaction,
    system: app_commands.Choice[str],
    role: discord.Role,
    option: Literal["add", "remove"],
):
    """Update the list of roles with config access."""

    fields_to_update: list[str] = []
    state = ""

    async with specified_guild_config(
        cast(Nightcore, interaction.client),
        cast(Guild, interaction.guild).id,
        config_type=GuildMetaConfig,
        _create=True,
    ) as (guild_config, _):
        if system.value == "all":
            fields_to_update = MetaConfigAccessTypeEnum.all_values()
        else:
            choice = MetaConfigAccessTypeEnum.from_choice(system.value)
            fields_to_update = [choice.value]

        for field_name in fields_to_update:
            current = getattr(guild_config, field_name)
            new_list, field_changed, state = update_id_list(
                current,
                role.id,
                option,
            )
            if field_changed:
                setattr(guild_config, field_name, new_list)

    if state == "exists":
        desc = f"Роль <@&{role.id}> уже в списке доступа."
        color = discord.Color.yellow()
    elif state == "absent":
        desc = f"Роль <@&{role.id}> не в списке доступа."
        color = discord.Color.red()
    elif state == "added":
        desc = f"Роль <@&{role.id}> добавлена в список доступа{'ко всем системам' if system.value == 'all' else ''}."  # noqa: E501
        color = discord.Color.blurple()
    else:  # removed
        desc = f"Роль <@&{role.id}> удалена из списка доступа{'всех систем' if system.value == 'all' else ''}."  # noqa: E501
        color = discord.Color.blurple()

    await interaction.response.send_message(
        embed=Embed(
            title="Настройка доступа к системе",
            description=desc,
            color=color,
        ),
        ephemeral=True,
    )

    logger.info(
        "[command] - invoked user=%s guild=%s option=%s role=%s system=%s",
        interaction.user.id,
        cast(Guild, interaction.guild).id,
        option,
        role.id,
        system.value,
    )
