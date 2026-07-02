"""Handle user items changed events."""

import logging
from typing import TYPE_CHECKING

import discord
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
from src.nightcore.utils.webhook import send_webhook_message

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

        await send_webhook_message(self.bot, dto)

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

        try:
            await member.send(view=view)
        except discord.Forbidden:
            logger.info(
                "[%s/log] Failed to send private message for user %s in guild %s because he doesn't accept DM",  # noqa: E501
                dto.event_type,
                dto.user_id,
                dto.guild.id,
            )
        except Exception as e:
            logger.warning(
                "[%s/log] Failed to send private message for user %s in guild %s: %s",  # noqa: E501
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
