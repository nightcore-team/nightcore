"""Handle decline coins shop order button."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, Message, Thread
from discord.interactions import Interaction

from src.infra.db.models import (
    GuildEconomyConfig,
    GuildLoggingConfig,
    GuildNotificationsConfig,
)
from src.infra.db.operations import (
    get_shop_order_state,
    get_specified_field,
    get_specified_webhook,
)
from src.nightcore.components.view.v2 import (
    ErrorViewV2,
    MissingPermissionsViewV2,
)
from src.nightcore.features.economy.components.v2 import CoinsShopOrderViewV2
from src.nightcore.features.economy.events.dto import CoinsShopOrderNotifyDTO
from src.nightcore.utils import has_any_role_from_sequence
from src.utils._enums import ChannelType, ShopOrderStateEnum

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


async def handle_decline_coins_shop_order_button(
    interaction: Interaction["Nightcore"],
):
    """Decline shop order button."""

    bot = interaction.client

    message = cast(Message, interaction.message)
    thread = cast(Thread, interaction.channel)
    guild = cast(Guild, interaction.guild)

    await interaction.response.defer()

    outcome = ""
    async with bot.uow.start() as session:
        shop_order = await get_shop_order_state(
            session=session,
            guild_id=guild.id,
            custom_id=thread.id,
        )

        economy_logging_webhook = await get_specified_webhook(
            session=session,
            guild_id=guild.id,
            config_type=GuildLoggingConfig,
            channel_type=ChannelType.LOGGING_ECONOMY,
        )

        economy_access_roles_ids = await get_specified_field(
            session,
            guild_id=guild.id,
            config_type=GuildEconomyConfig,
            field_name="economy_access_roles_ids",
        )
        if not economy_access_roles_ids:
            outcome = "economy_access_not_configured"

        if not has_any_role_from_sequence(
            cast(Member, interaction.user),
            economy_access_roles_ids,
        ):
            outcome = "missing_permissions"
        else:
            nightcore_notifications_webhook = await get_specified_webhook(
                session=session,
                guild_id=guild.id,
                config_type=GuildNotificationsConfig,
                channel_type=ChannelType.NIGHTCORE_NOTIFICATIONS,
            )

            if not shop_order:
                outcome = "order_not_found"

            if not outcome:
                if shop_order.state != ShopOrderStateEnum.PENDING:  # type: ignore
                    outcome = "invalid_state"
                else:
                    shop_order.state = ShopOrderStateEnum.DENIED  # type: ignore
                    outcome = "success"

                    await session.delete(shop_order)

    if outcome == "economy_access_not_configured":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка отклонения покупки",
                "Роли с доступом к экономике не настроены.",
            )
        )
        return

    if outcome == "missing_permissions":
        await interaction.response.send_message(
            view=MissingPermissionsViewV2(),
            ephemeral=True,
        )
        return

    if outcome == "order_not_found":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка отклонения покупки",
                "Заказ не найден в базе данных.",
            )
        )
        return

    elif outcome == "invalid_state":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка отклонения покупки",
                "Заказ уже был обработан ранее.",
            )
        )

    elif outcome == "success":
        assert shop_order is not None

        await interaction.followup.send(
            view=ErrorViewV2(
                "Покупка отклонена",
                f"Покупка товара **{shop_order.payload.get('item')}** "
                "была отклонена.",
            ),
            ephemeral=False,
        )

        view = CoinsShopOrderViewV2(
            ping_roles_ids=None,
            user_id=shop_order.user_id,
            user_balance_before=shop_order.payload.get("balance_before"),
            user_balance_after=shop_order.payload.get("balance_after"),
            item_name=shop_order.payload.get("item"),
            item_price=shop_order.payload.get("cost"),
            disable_buttons=True,
        )

        try:
            await message.edit(view=view)
            await thread.edit(archived=True, locked=True)
        except Exception as e:
            logger.error(
                "[economy] Error occurred while editing message and "
                "thread: %s",
                e,
            )
            return

        bot.dispatch(
            "coins_shop_order_notify",
            dto=CoinsShopOrderNotifyDTO(
                guild=guild,
                event_type="coins_shop_order_notify",
                user_id=shop_order.user_id,
                moderator_id=interaction.user.id,
                state=ShopOrderStateEnum.DENIED,
                item_name=shop_order.payload.get("item"),
                item_cost=shop_order.payload.get("cost"),
                user_balance_before=shop_order.payload.get("balance_before"),
                user_balance_after=shop_order.payload.get("balance_after"),
                custom_id=thread.id,
                logging_webhook=economy_logging_webhook,
                notifications_webhook=nightcore_notifications_webhook,  # type: ignore
            ),
        )
