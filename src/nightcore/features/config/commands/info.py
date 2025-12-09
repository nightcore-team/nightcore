"""Subgroup to configure levels settings."""

import logging
from typing import cast

from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.operations import get_config_type_by_name
from src.nightcore.bot import Nightcore
from src.nightcore.features.config.components.v2 import ConfigInfoViewV2
from src.nightcore.features.config.utils.pages import build_guild_config_pages
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


class ConfigInfo(Cog):
    def __init__(self, bot: Nightcore):
        self.bot = bot

    @app_commands.command(
        name="config_info",
        description="Получение информации о конфигурации системы.",
    )  # type: ignore
    @app_commands.describe(
        system="Выберите систему, информацию о которой хотите получить."
    )
    @app_commands.choices(
        system=[
            app_commands.Choice(name="Кланы", value="clans"),
            app_commands.Choice(name="Экономика", value="economy"),
            app_commands.Choice(name="Инфомейкер", value="infomaker"),
            app_commands.Choice(name="Уровни", value="levels"),
            app_commands.Choice(name="Логирование", value="logging"),
            app_commands.Choice(name="Модерация", value="moderation"),
            app_commands.Choice(name="Уведомления", value="notifications"),
            app_commands.Choice(name="Другое", value="other"),
            app_commands.Choice(
                name="Приватные каналы", value="private_channels"
            ),
            app_commands.Choice(name="Тикеты", value="tickets"),
        ]
    )
    @check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)  # type: ignore
    async def config_info(
        self,
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


async def setup(bot: Nightcore):
    """Setup the ConfigInfo cog."""
    await bot.add_cog(ConfigInfo(bot))
