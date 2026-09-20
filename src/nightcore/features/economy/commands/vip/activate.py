"""Command to activate a user's VIP-status."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild
from discord.interactions import Interaction

from src.infra.db.operations import (
    get_guild_vip_statuses,
    get_user_vip_statuses_for_update,
)
from src.nightcore.components.view.v2 import ErrorViewV2
from src.nightcore.features.economy._groups import vip as vip_group
from src.nightcore.features.economy.components.v2 import (
    VipStatusActivateViewV2,
)
from src.nightcore.features.economy.utils.pages import (
    build_user_vip_statuses_content,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@vip_group.command(
    name="activate", description="Активировать свой VIP-status."
)  # type: ignore
@check_required_permissions(PermissionsFlagEnum.NONE)
async def activate_vip(interaction: Interaction["Nightcore"]):
    """Show the user's VIP-statuses and their activation buttons."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    async with bot.uow.start() as session:
        user_vip_statuses = await get_user_vip_statuses_for_update(
            session,
            guild_id=guild.id,
            user_id=interaction.user.id,
            for_update=False,
        )
        guild_vip_statuses = await get_guild_vip_statuses(
            session, guild_id=guild.id
        )

    content, statuses = build_user_vip_statuses_content(
        user_vip_statuses, guild_vip_statuses
    )

    if not statuses:
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Активация VIP-status",
                "У вас нет доступных VIP-статусов.",
            ),
            ephemeral=True,
        )
        return

    view = VipStatusActivateViewV2(
        bot=bot,
        content=content,
        statuses=statuses,
    )

    await interaction.response.send_message(view=view, ephemeral=True)

    logger.info(
        "[command] - invoked user=%s guild=%s",
        interaction.user.id,
        guild.id,
    )
