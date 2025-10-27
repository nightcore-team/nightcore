"""Module for clan shop notification events."""

import logging
from typing import TYPE_CHECKING

from discord.ext.commands import Cog  # type: ignore

from src.nightcore.features.economy.components.v2 import (
    CoinsShopOrderNotifyViewV2,
)
from src.nightcore.utils import (
    ensure_guild_exists,
    ensure_member_exists,
    ensure_messageable_channel_exists,
)

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
        guild = await ensure_guild_exists(self.bot, dto.guild.id)
        if not guild:
            logger.error(
                "[clans/shop/notify] Guild %s not found for shop purchase notification.",  # noqa: E501
                dto.guild.id,
            )
            return

        member = await ensure_member_exists(guild, dto.user_id)
        if not member:
            logger.error(
                "[clans/shop/notify] Member %s not found in guild %s for shop purchase notification.",  # noqa: E501
                dto.user_id,
                dto.guild.id,
            )
            return

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
            await member.send(
                view=view,
            )
        except Exception as e:
            logger.error(
                "[clans/shop/notify] Error occurred while processing shop purchase notification for member %s in guild %s: %s",  # noqa: E501
                dto.user_id,
                dto.guild.id,
                e,
            )

            if not dto.notifications_channel_id:
                logger.error(
                    "[clans/shop/notify] No notifications channel configured for guild %s.",  # noqa: E501
                    dto.guild.id,
                )
                return
            else:
                channel = await ensure_messageable_channel_exists(
                    guild, dto.notifications_channel_id
                )
                if not channel:
                    logger.error(
                        "[clans/shop/notify] Notifications channel %s not found in guild %s.",  # noqa: E501
                        dto.notifications_channel_id,
                        dto.guild.id,
                    )
                    return

                try:
                    await channel.send(  # type: ignore
                        view=view,
                    )
                except Exception as e:
                    logger.error(
                        "[clans/shop/notify] Error sending notification to channel %s in guild %s: %s",  # noqa: E501
                        dto.notifications_channel_id,
                        dto.guild.id,
                        e,
                    )
                    return


async def setup(bot: "Nightcore") -> None:
    """Setup the CoinsShopNotifyEvent cog."""
    await bot.add_cog(CoinsShopNotifyEvent(bot))
