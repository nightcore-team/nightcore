"""Handle coins shop order notifications."""

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext.commands import Cog  # type: ignore

from src.nightcore.features.economy.components.v2 import (
    CoinsShopOrderNotifyViewV2,
)
from src.nightcore.utils import (
    ensure_member_exists,
)
from src.nightcore.utils.webhook import send_to_webhook, send_webhook_message

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

        await send_webhook_message(self.bot, dto)

        member = await ensure_member_exists(dto.guild, dto.user_id)
        if member is None:
            logger.info(
                "[%s/log] Member %s not found in guild %s.",
                dto.event_type,
                dto.user_id,
                dto.guild.id,
            )
            return

        if not dto.notifications_webhook or not dto.notifications_webhook.valid:
            logger.info(
                "[%s/log] No notifications webhook configured for guild %s.",
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
            except discord.Forbidden:
                logger.info(
                    "[%s/log] Failed to send DM to user %s because he doesn't accept DM. Trying notifications channel...",  # noqa: E501
                    dto.event_type,
                    dto.user_id,
                )
            except Exception as e:
                logger.warning(
                    "[%s/log] Failed to send DM to user %s in guild %s: %s. Trying notifications channel...",  # noqa: E501
                    dto.event_type,
                    dto.user_id,
                    dto.guild.id,
                    e,
                )
            finally:
                # fallback
                if dto.notifications_webhook and dto.notifications_webhook.valid:
                    await send_to_webhook(
                        self.bot,
                        dto.notifications_webhook,
                        view,
                        context=dto.event_type,
                        guild_id=dto.guild.id,
                    )

        logger.info(
            "[%s/log] - invoked user=%s guild=%s item_name=%s item_price=%s balance_before=%s balance_after=%s",  # noqa: E501
            dto.event_type,
            dto.user_id,
            dto.guild.id,
            dto.item_name,
            dto.item_price,
            dto.user_balance_before,
            dto.user_balance_after,
        )


async def setup(bot: "Nightcore") -> None:
    """Setup the CoinsShopNotifyEvent cog."""
    await bot.add_cog(CoinsShopNotifyEvent(bot))
