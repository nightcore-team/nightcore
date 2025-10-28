"""Module for clan shop notification events."""

import asyncio
import logging
from collections.abc import Awaitable
from typing import TYPE_CHECKING, Any

from discord.ext.commands import Cog  # type: ignore

from src.nightcore.features.economy.components.v2 import (
    CoinsShopOrderNotifyViewV2,
)
from src.nightcore.utils import (
    ensure_member_exists,
    ensure_messageable_channel_exists,
)
from src.nightcore.utils.log import send_log_message

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore
    from src.nightcore.features.economy.events.dto import (
        CoinsShopOrderNotifyDTO,
    )

logger = logging.getLogger(__name__)


class CoinsShopNotifyEvent(Cog):
    def __init__(self, bot: "Nightcore"):
        self.bot = bot

    @Cog.listener()
    async def on_coins_shop_order_notify(
        self, dto: "CoinsShopOrderNotifyDTO"
    ) -> None:
        """Handle coins shop purchase notification event."""

        member = await ensure_member_exists(dto.guild, dto.user_id)
        if not member:
            logger.error(
                "[%s/log] Member %s not found in guild %s.",
                dto.event_type,
                dto.user_id,
                dto.guild.id,
            )

        gather_list: list[Awaitable[Any]] = []

        gather_list.append(send_log_message(bot=self.bot, dto=dto))

        notifications_channel = None
        if dto.notifications_channel_id:
            notifications_channel = await ensure_messageable_channel_exists(
                dto.guild, dto.notifications_channel_id
            )
            if not notifications_channel:
                logger.error(
                    "[%s/log] Notifications channel %s not found in guild %s.",
                    dto.event_type,
                    dto.notifications_channel_id,
                    dto.guild.id,
                )
        else:
            logger.error(
                "[%s/log] No notifications channel ID provided for guild %s.",
                dto.event_type,
                dto.guild.id,
            )

        if member:
            view = CoinsShopOrderNotifyViewV2(
                bot=self.bot,
                moderator_id=dto.moderator_id,
                state=dto.state,
                item_name=dto.item_name,
                item_price=dto.item_price,
                user_balance_before=dto.user_balance_before,
                user_balance_after=dto.user_balance_after,
                custom_id=dto.custom_id,
            )

            try:
                await member.send(view=view)
                logger.info(
                    "[%s/log] Successfully sent DM to user %s in guild %s.",
                    dto.event_type,
                    dto.user_id,
                    dto.guild.id,
                )
            except Exception as e:
                logger.warning(
                    "[%s/log] Failed to send DM to user %s in guild %s: %s. Trying notifications channel...",  # noqa: E501
                    dto.event_type,
                    dto.user_id,
                    dto.guild.id,
                    e,
                )

                # fallback
                if notifications_channel:
                    gather_list.append(
                        notifications_channel.send(  # type: ignore
                            view=view,
                        )
                    )
                else:
                    logger.error(
                        "[%s/log] No notifications channel available for fallback for user %s in guild %s.",  # noqa: E501
                        dto.event_type,
                        dto.user_id,
                        dto.guild.id,
                    )

        try:
            await asyncio.gather(*gather_list, return_exceptions=True)
        except Exception as e:
            logger.exception(
                "[%s/log] Failed to run gather for user %s in guild %s: %s",
                dto.event_type,
                dto.user_id,
                dto.guild.id,
                e,
            )


async def setup(bot: "Nightcore") -> None:
    """Setup the CoinsShopNotifyEvent cog."""
    await bot.add_cog(CoinsShopNotifyEvent(bot))
