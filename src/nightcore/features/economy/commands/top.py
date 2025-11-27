"""Command to show top 10 users on the server."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.operations import get_specified_field, get_users_by_spec
from src.nightcore.features.economy.components.v2 import UsersListViewV2

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


class Top(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(
        name="top", description="Показать топ 10 пользователей на сервере"
    )  # type: ignore
    @app_commands.describe(sort_by="Критерий сортировки топа пользователей")
    @app_commands.choices(
        sort_by=[
            app_commands.Choice(name="Голосовая активность", value="voice"),
            app_commands.Choice(name="Коины", value="coins"),
            app_commands.Choice(name="Уровень", value="level"),
            app_commands.Choice(name="Сообщения", value="messages"),
        ]
    )
    @app_commands.guild_only()
    @check_required_permissions(PermissionsFlagEnum.NONE)  # type: ignore
    async def top(
        self,
        interaction: Interaction["Nightcore"],
        sort_by: app_commands.Choice[str] | None = None,
    ) -> None:
        """Get list of clans by specified choice."""

        guild = cast(Guild, interaction.guild)

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

        view = UsersListViewV2(
            interaction.client,
            coin_name=coin_name,
            users=users,
            sort_by=sort_by.value if sort_by else None,
        )

        await interaction.response.send_message(view=view, ephemeral=True)

        logger.info(
            "[command] - invoked user=%s guild=%s sort_by=%s",
            interaction.user.id,
            guild.id,
            sort_by.value if sort_by else "default",
        )


async def setup(bot: "Nightcore") -> None:
    """Setup the Top cog."""
    await bot.add_cog(Top(bot))
