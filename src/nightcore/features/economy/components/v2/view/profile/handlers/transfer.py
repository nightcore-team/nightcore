"""
User profile transfer history handler.

Handles opening the transfer history view in an ephemeral message.
"""

import logging
from typing import TYPE_CHECKING

from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.operations import (
    get_specified_field,
    get_user_transfer_history,
)
from src.nightcore.features.economy.utils.pages import (
    build_transfer_history_pages,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


async def open_transfer_history(
    interaction: Interaction["Nightcore"],
    *,
    guild_id: int,
    user_id: int,
) -> None:
    """Open the transfer history view for a user in an ephemeral message."""

    from ...transfer import TransferHistoryViewV2

    bot = interaction.client

    async with bot.uow.start() as session:
        coin_name: str | None = await get_specified_field(
            session,
            guild_id=guild_id,
            config_type=GuildEconomyConfig,
            field_name="coin_name",
        )
        transfers = await get_user_transfer_history(
            session, guild_id=guild_id, user_id=user_id
        )
        logger.info("TRANSFERS: %s", transfers)

    pages = build_transfer_history_pages(transfers, coin_name)

    view = TransferHistoryViewV2(
        bot=bot,
        user_id=user_id,
        total_transfers=len(transfers),
        pages=pages,
    )

    await interaction.response.send_message(
        view=view.make_component(),
        ephemeral=True,
    )
