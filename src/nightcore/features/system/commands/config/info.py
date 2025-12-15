"""Subcommand to check each system settings."""

import logging
from typing import cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.models._enums import MetaConfigAccessTypeEnum
from src.infra.db.operations import get_config_type_by_name
from src.nightcore.bot import Nightcore
from src.nightcore.features.system._groups import config as config_system_group
from src.nightcore.features.system.components.v2 import ConfigInfoViewV2
from src.nightcore.features.system.utils.pages import build_guild_config_pages
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


@config_system_group.command(
    name="info",
    description="Получение информации о конфигурации системы.",
)  # type: ignore
@app_commands.describe(
    system="Выберите систему, информацию о которой хотите получить."
)
@app_commands.choices(
    system=[
        app_commands.Choice(name="Мета", value="meta"),
        *[
            app_commands.Choice(name=name, value=value)
            for name, value in MetaConfigAccessTypeEnum.choices()
        ],
    ]
)
@check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)  # type: ignore
async def config_info(
    interaction: Interaction[Nightcore],
    system: app_commands.Choice[str],
    ephemeral: bool = True,
):
    """Configure levels settings for the guild."""

    configt = get_config_type_by_name(system.value)  # type: ignore

    async with specified_guild_config(
        interaction.client,
        cast(Guild, interaction.guild).id,
        config_type=configt,  # type: ignore
        _create=True,
    ) as (guild_config, _):  # type: ignore
        pages = build_guild_config_pages(guild_config, is_v2=True)  # type: ignore

    view = ConfigInfoViewV2(
        bot=interaction.client,
        author_id=interaction.user.id,
        pages=pages,
        config_name=system.name,
    ).make_component()

    await interaction.response.send_message(view=view, ephemeral=ephemeral)

    logger.info(
        "[command] - invoked user=%s guild=%s",
        interaction.user.id,
        cast(Guild, interaction.guild).id,
    )
