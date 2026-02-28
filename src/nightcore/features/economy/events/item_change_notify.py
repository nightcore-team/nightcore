"""Handle item change notify events."""

import logging
from typing import TYPE_CHECKING

from discord.ext.commands import Cog  # type: ignore

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore
    from src.nightcore.features.economy.events.dto.item_change import (
        ItemChangeNotifyEventDTO,
    )

from src.nightcore.utils.log import send_log_message

logger = logging.getLogger(__name__)


class ItemChangeNotifyEvent(Cog):
    def __init__(self, bot: "Nightcore"):
        self.bot = bot

    @Cog.listener()
    async def on_item_change_notify(
        self,
        dto: "ItemChangeNotifyEventDTO",
    ):
        """Handle user items changed event."""

        if dto.logging_channel_id:
            try:
                await send_log_message(self.bot, dto)
            except Exception as e:
                logger.warning(
                    "[%s/log] Failed to send log message for guild %s: %s. log embed: %s",  # noqa: E501
                    dto.event_type,
                    dto.guild.id,
                    e,
                    dto.build_log_embed(self.bot).to_dict(),
                )
        else:
            logger.info(
                "[%s/log] No logging channel ID provided for guild %s",
                dto.event_type,
                dto.guild.id,
            )

        logger.info(
            "[%s/log] - invoked guild=%s item_name=%s",
            dto.event_type,
            dto.guild.id,
            dto.item_name,
        )


async def setup(bot: "Nightcore") -> None:
    """Setup the ItemChangeNotifyEvent cog."""
    await bot.add_cog(ItemChangeNotifyEvent(bot))
