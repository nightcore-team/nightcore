"""Subgroup to configure other settings."""

import logging
from typing import Literal, cast

import discord
from discord import Guild, app_commands
from discord.embeds import Embed
from discord.interactions import Interaction

from src.infra.db.models.guild import MainGuildConfig
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import NoOptionsSuppliedEmbed
from src.nightcore.features.config._groups import other as other_group
from src.nightcore.features.config.utils import (
    org_roles_dict_value,
)
from src.nightcore.services.config import (
    specified_guild_config,
)
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


@other_group.command(
    name="setup", description="Настроить остальные настройки."
)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    rules_channel="Канал для правил",
    proposal_channel="Канал для предложений",
    organizational_roles="Организационные роли. Формат: org name, tag, role_id | org name, tag, role_id | ...",  # noqa: E501
    fraction_roles="Фракционные роли. Формат: role_id, role_id, ...",
    role_request_channel="Канал для проверки запросов на роли",
)
async def setup(
    interaction: Interaction,
    rules_channel: discord.TextChannel | None = None,  #
    proposal_channel: discord.TextChannel | None = None,  #
    # voice_temp_roles: str | None = None,  #
    organizational_roles: str | None = None,  #
    fraction_roles: str | None = None,  #
    role_request_channel: discord.TextChannel | None = None,  #
):
    """Configure moderation settings."""

    specs: list[FieldSpec | None] = [
        int_id_value("rules_channel_id", rules_channel),
        int_id_value("create_proposal_channel_id", proposal_channel),
        int_id_value("check_role_requests_channel_id", role_request_channel),
        org_roles_dict_value("organizational_roles", organizational_roles),
        # temp_voice_roles_dict_value("voice_temp_roles", voice_temp_roles),
        list_csv("fraction_roles", fraction_roles),
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
        config_type=MainGuildConfig,
        _create=True,
    ) as (guild_config, _):
        changes = apply_field_changes(guild_config, specs)  # type: ignore

    changed, skipped = split_changes(changes)
    description = format_changes(changed, skipped)

    await interaction.response.send_message(
        embed=Embed(
            title="Остальные настройки",
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


@other_group.command(
    name="update_fraction_roles", description="Обновить фракционные роли"
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
    option="Добавить или удалить роль из списка фракционных ролей",
)
async def update_fraction_roles(
    interaction: Interaction,
    role: discord.Role,
    option: Literal["add", "remove"],
):
    """Update the list of roles with ban access."""
    async with specified_guild_config(
        cast(Nightcore, interaction.client),
        cast(Guild, interaction.guild).id,
        config_type=MainGuildConfig,
    ) as (guild_config, _):
        new_list, changed, state = update_id_list(
            guild_config.fraction_roles,
            role.id,
            option,
        )
        if changed:
            guild_config.fraction_roles = new_list

    if state == "exists":
        desc = f"Роль <@&{role.id}> уже в списке фракционных ролей."
        color = discord.Color.yellow()
    elif state == "absent":
        desc = f"Роль <@&{role.id}> не в списке фракционных ролей."
        color = discord.Color.red()
    elif state == "added":
        desc = f"Роль <@&{role.id}> добавлена в список фракционных ролей."
        color = discord.Color.blurple()
    else:
        desc = f"Роль <@&{role.id}> удалена из списка фракционных ролей."
        color = discord.Color.blurple()

    await interaction.response.send_message(
        embed=Embed(
            title="Остальные настройки",
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
