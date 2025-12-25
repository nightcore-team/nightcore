"""Clan manage notify event handler."""

import logging
from typing import TYPE_CHECKING

from discord.ext.commands import Cog  # type: ignore

from src.nightcore.features.clans.events.dto.clan_manage_notify import (
    ClanManageNotifyDTO,
)
from src.nightcore.utils.log import send_log_message

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class ClanManageNotifyEvent(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @Cog.listener()
    async def on_clan_manage_notify(self, dto: ClanManageNotifyDTO):
        """Handle clan manage notify event."""

        await send_log_message(self.bot, dto)

        logger.info(
            "[%s/log] - invoked user=%s guild=%s actions=%s",
            dto.event_type,
            dto.actor_id,
            dto.guild.id,
            [
                f"\nt={action.type} b={action.before} a={action.after}"
                for action in dto.actions
            ],
        )


async def setup(bot: "Nightcore"):
    """Setup the ClanChangeNotifyEvent cog."""
    await bot.add_cog(ClanManageNotifyEvent(bot))
