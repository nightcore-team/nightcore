"""Command to show top clans on the server."""

import logging
import time
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.operations import get_clans_by_spec
from src.nightcore.features.clans._groups import clan as clan_main_group
from src.nightcore.features.clans.components.v2 import ClanListViewV2
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


@clan_main_group.command(
    name="top",
    description="Показать топ 10 кланов на сервере",  # type: ignore
)
@app_commands.describe()
@app_commands.choices(
    sort_by=[
        app_commands.Choice(name="Участники", value="members"),
        app_commands.Choice(name="Репутация", value="reputation"),
        app_commands.Choice(name="Дата создания", value="created_at"),
    ]
)
@check_required_permissions(PermissionsFlagEnum.NONE)
async def clan_top(
    interaction: Interaction["Nightcore"],
    sort_by: app_commands.Choice[str] | None = None,
) -> None:
    """Get list of clans by specified choice."""

    guild = cast(Guild, interaction.guild)

    start_time = time.perf_counter()
    async with interaction.client.uow.start() as session:
        clans = await get_clans_by_spec(
            session,
            guild_id=guild.id,
            spec=sort_by.value if sort_by else None,
            limit=10,
        )

    end_time = time.perf_counter()
    logger.info(
        "[clan/top] Fetched clans for guild %s in %.4f seconds",
        guild.id,
        end_time - start_time,
    )

    start_time = time.perf_counter()
    view = ClanListViewV2(
        interaction.client, clans, sort_by=sort_by.value if sort_by else None
    )
    end_time = time.perf_counter()
    logger.info(
        "[clan/top] Created ClanListViewV2 for guild %s in %.4f seconds",
        guild.id,
        end_time - start_time,
    )

    start_time = time.perf_counter()
    await interaction.response.send_message(view=view, ephemeral=True)
    end_time = time.perf_counter()

    logger.info(
        "[clan/top] Sent clan top message for guild %s in %.4f seconds",
        guild.id,
        end_time - start_time,
    )
