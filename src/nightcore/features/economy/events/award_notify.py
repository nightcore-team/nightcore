"""Handle user items changed events."""

import asyncio
import logging
from collections.abc import Awaitable
from typing import TYPE_CHECKING, Any

from discord.ext.commands import Cog  # type: ignore

from src.nightcore.features.economy.components.v2 import (
    AwardNotificationViewV2,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore
    from src.nightcore.features.economy.events.dto import (
        AwardNotificationEventDTO,
    )

from src.nightcore.utils import (
    ensure_member_exists,
)
from src.nightcore.utils.log import send_log_message

logger = logging.getLogger(__name__)


class UserItemsChangedEvent(Cog):
    def __init__(self, bot: "Nightcore"):
        self.bot = bot

    @Cog.listener()
    async def on_user_items_changed(
        self,
        dto: "AwardNotificationEventDTO",
    ):
        """Handle user items changed event."""

        member = await ensure_member_exists(dto.guild, dto.user_id)
        if not member:
            logger.error(
                "[%s/log] Member %s not found in guild %s",
                dto.event_type,
                dto.user_id,
                dto.guild.id,
            )
            return

        view = AwardNotificationViewV2(
            bot=self.bot,
            user_id=dto.moderator_id,
            item_name=dto.item_name,
            amount=dto.amount,
            reason=dto.reason,
        )

        gather_list: list[Awaitable[Any]] = []

        if dto.logging_channel_id:
            gather_list.append(send_log_message(self.bot, dto))
        else:
            logger.error(
                "[%s/log] No logging channel ID provided for guild %s",
                dto.event_type,
                dto.guild.id,
            )

        gather_list.append(member.send(view=view))

        try:
            await asyncio.gather(*gather_list)
        except Exception as e:
            logger.exception(
                "[%s/log] Failed to run gather for user %s in guild %s: %s",
                dto.event_type,
                dto.user_id,
                dto.guild.id,
                e,
            )

        logger.info(
            "[%s/log] - invoked user=%s guild=%s item_name=%s amount=%s",
            dto.event_type,
            dto.user_id,
            dto.guild.id,
            dto.item_name,
            dto.amount,
        )


async def setup(bot: "Nightcore") -> None:
    """Setup the UserItemsChangedEvent cog."""
    await bot.add_cog(UserItemsChangedEvent(bot))
