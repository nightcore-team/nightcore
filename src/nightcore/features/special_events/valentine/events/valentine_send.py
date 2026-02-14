"""Handle valentine send event."""

import logging
from typing import TYPE_CHECKING

from discord.ext.commands import Cog  # type: ignore

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.features.special_events.valentine.events.dto.valentine_send import (  # noqa: E501
    ValentineSendEventDTO,
)
from src.nightcore.utils.log import send_log_message

logger = logging.getLogger(__name__)


class ValentineSendEvent(Cog):
    def __init__(self, bot: "Nightcore"):
        self.bot = bot

    @Cog.listener()
    async def on_valentine_send(
        self,
        dto: "ValentineSendEventDTO",
    ):
        """Handle valentine send event."""

        await send_log_message(self.bot, dto)

        logger.info(
            "[%s/log] - invoked user=%s guild=%s",
            dto.event_type,
            dto.user_id,
            dto.guild.id,
        )


async def setup(bot: "Nightcore") -> None:
    """Setup the UserItemsChangedEvent cog."""
    await bot.add_cog(ValentineSendEvent(bot))
