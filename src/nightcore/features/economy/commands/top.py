"""Command to show top clans on the server."""

import logging
import time
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.operations import get_specified_field, get_users_by_spec
from src.nightcore.features.economy.components.v2 import UsersListViewV2

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class Top(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(
        name="top", description="Показать топ 10 пользователей на сервере"
    )
    @app_commands.describe()
    @app_commands.choices(
        sort_by=[
            app_commands.Choice(name="Голосовая активность", value="voice"),
            app_commands.Choice(name="Коины", value="coins"),
            app_commands.Choice(name="Уровень", value="level"),
            app_commands.Choice(name="Сообщения", value="messages"),
        ]
    )
    async def top(
        self,
        interaction: Interaction["Nightcore"],
        sort_by: app_commands.Choice[str] | None = None,
    ) -> None:
        """Get list of clans by specified choice."""

        guild = cast(Guild, interaction.guild)

        start_time = time.perf_counter()
        async with interaction.client.uow.start() as session:
            users = await get_users_by_spec(
                session,
                guild_id=guild.id,
                spec=sort_by.value if sort_by else None,
            )

            coin_name = await get_specified_field(
                session,
                guild_id=guild.id,
                config_type=GuildEconomyConfig,
                field_name="coin_name",
            )

        end_time = time.perf_counter()
        logger.info(
            "[users/top] Fetched users for guild %s in %.4f seconds",
            guild.id,
            end_time - start_time,
        )

        start_time = time.perf_counter()
        view = UsersListViewV2(
            interaction.client,
            coin_name=coin_name,
            users=users,
            sort_by=sort_by.value if sort_by else None,
        )
        end_time = time.perf_counter()
        logger.info(
            "[users/top] Created UserListViewV2 for guild %s in %.4f seconds",
            guild.id,
            end_time - start_time,
        )

        start_time = time.perf_counter()
        await interaction.response.send_message(view=view, ephemeral=True)
        end_time = time.perf_counter()

        logger.info(
            "[users/top] Sent user top message for guild %s in %.4f seconds",
            guild.id,
            end_time - start_time,
        )


async def setup(bot: "Nightcore") -> None:
    """Setup the Top cog."""
    await bot.add_cog(Top(bot))
