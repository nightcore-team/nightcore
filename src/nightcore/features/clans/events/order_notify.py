"""Module for clan shop notification events."""

import asyncio
import logging
from collections.abc import Awaitable
from typing import TYPE_CHECKING, Any

from discord.ext.commands import Cog  # type: ignore

from src.nightcore.features.clans.components.v2 import ShopNotifyViewV2
from src.nightcore.utils import (
    ensure_member_exists,
)
from src.nightcore.utils.webhook import send_to_webhook, send_webhook_message

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore
    from src.nightcore.features.clans.events.dto import (
        ClanShopOrderNotifyDTO,
    )

logger = logging.getLogger(__name__)


class ClanShopNotifyEvent(Cog):
    def __init__(self, bot: "Nightcore"):
        self.bot = bot

    @Cog.listener()
    async def on_clan_shop_order_notify(
        self, dto: "ClanShopOrderNotifyDTO"
    ) -> None:
        """Handle clan shop purchase notification event."""

        member = await ensure_member_exists(dto.guild, dto.user_id)
        if not member:
            logger.error(
                "[%s/log] Member %s not found in guild %s.",
                dto.event_type,
                dto.user_id,
                dto.guild.id,
            )

        gather_list: list[Awaitable[Any]] = []

        gather_list.append(send_webhook_message(bot=self.bot, dto=dto))

        if not dto.notifications_webhook or not dto.notifications_webhook.valid:
            logger.error(
                "[%s/log] No notifications webhook configured for guild %s.",
                dto.event_type,
                dto.guild.id,
            )

        # Намагаємось відправити в ДМ
        if member:
            view = ShopNotifyViewV2(
                bot=self.bot,
                moderator_id=dto.moderator_id,
                state=dto.state,
                clan_name=dto.clan_name,
                item_name=dto.item_name,
                item_price=dto.item_price,
                clan_balance_before=dto.clan_balance_before,
                clan_balance_after=dto.clan_balance_after,
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
                if dto.notifications_webhook and dto.notifications_webhook.valid:
                    gather_list.append(
                        send_to_webhook(
                            self.bot,
                            dto.notifications_webhook,
                            view,
                            context=dto.event_type,
                            guild_id=dto.guild.id,
                        )
                    )
                else:
                    logger.error(
                        "[%s/log] No notifications webhook available for fallback for user %s in guild %s.",  # noqa: E501
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

        logger.info(
            "[%s/log] - invoked user=%s guild=%s item_name=%s item_price=%s balance_before=%s balance_after=%s",  # noqa: E501
            dto.event_type,
            dto.user_id,
            dto.guild.id,
            dto.item_name,
            dto.item_price,
            dto.clan_balance_before,
            dto.clan_balance_after,
        )


async def setup(bot: "Nightcore") -> None:
    """Setup the ClanShopNotifyEvent cog."""
    await bot.add_cog(ClanShopNotifyEvent(bot))
