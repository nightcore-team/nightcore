"""Command to show top 10 users on the server."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.operations import get_specified_field, get_users_by_spec
from src.nightcore.features.economy.components.v2 import UsersListViewV2
from src.nightcore.features.special_events.valentine._groups import (
    valentine as valentine_group,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


@valentine_group.command(
    name="top",
    description="Показать топ 10 пользователей на сервере по отправленным/полученным валентинкам",  # noqa: E501
)  # type: ignore
@app_commands.describe(sort_by="Критерий сортировки топа пользователей")
@app_commands.choices(
    sort_by=[
        app_commands.Choice(name="Отправленные валентинки", value="sent"),
        app_commands.Choice(name="Полученные валентинки", value="received"),
    ]
)
@app_commands.guild_only()
@check_required_permissions(PermissionsFlagEnum.NONE)  # type: ignore
async def top(
    interaction: Interaction["Nightcore"],
    sort_by: app_commands.Choice[str],
) -> None:
    """Get list of users by specified choice."""

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
