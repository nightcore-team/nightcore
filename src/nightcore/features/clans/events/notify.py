"""Module for clan shop notification events."""

import logging
from typing import TYPE_CHECKING

from discord.ext.commands import Cog  # type: ignore

from src.nightcore.features.clans.components.v2 import ShopNotifyViewV2
from src.nightcore.utils import ensure_guild_exists, ensure_member_exists

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore
    from src.nightcore.features.clans.events.dto.notify import (
        ClanShopPurchaseNotifyDTO,
    )

logger = logging.getLogger(__name__)


class ClanShopNotifyEvent(Cog):
    def __init__(self, bot: "Nightcore"):
        self.bot = bot

    @Cog.listener()
    async def on_clan_shop_purchase(
        self, dto: "ClanShopPurchaseNotifyDTO"
    ) -> None:
        """Handle clan shop purchase notification event."""
        guild = await ensure_guild_exists(self.bot, dto.guild_id)
        if not guild:
            logger.error(
                "[clans/shop/notify] Guild %s not found for shop purchase notification.",  # noqa: E501
                dto.guild_id,
            )
            return

        member = await ensure_member_exists(guild, dto.user_id)
        if not member:
            logger.error(
                "[clans/shop/notify] Member %s not found in guild %s for shop purchase notification.",  # noqa: E501
                dto.user_id,
                dto.guild_id,
            )
            return

        try:
            view = ShopNotifyViewV2(
                bot=self.bot,
                moderator_id=dto.moderator_id,
                state=dto.state,
                clan_name=dto.clan_name,
                clan_role_id=dto.clan_role_id,
                item_name=dto.item_name,
                item_price=dto.item_price,
                clan_balance_before=dto.clan_balance_before,
                custom_id=dto.custom_id,
            )

            await member.send(
                view=view,
            )
        except Exception as e:
            logger.error(
                "[clans/shop/notify] Error occurred while processing shop purchase notification for member %s in guild %s: %s",  # noqa: E501
                dto.user_id,
                dto.guild_id,
                e,
            )
            return


async def setup(bot: "Nightcore") -> None:
    """Setup the ClanShopNotifyEvent cog."""
    await bot.add_cog(ClanShopNotifyEvent(bot))
