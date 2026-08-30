"""Handle approve clan shop button."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, Message, Thread
from discord.interactions import Interaction

from src.infra.db.models import (
    GuildClansConfig,
    GuildLoggingConfig,
    GuildNotificationsConfig,
)
from src.infra.db.operations import (
    get_clan_by_name,
    get_shop_order_state,
    get_specified_field,
    get_specified_webhook,
)
from src.nightcore.components.view.v2 import (
    ErrorViewV2,
    MissingPermissionsViewV2,
    SuccessViewV2,
)
from src.nightcore.features.clans.components.v2 import ClanShopViewV2
from src.nightcore.features.clans.events.dto import ClanShopOrderNotifyDTO
from src.nightcore.utils import has_any_role_from_sequence
from src.utils._enums import ChannelType, ShopOrderStateEnum

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


async def handle_approve_clan_shop_button(
    interaction: Interaction["Nightcore"],
):
    """Approve shop request button."""

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

        clans_logging_webhook = await get_specified_webhook(
            session=session,
            guild_id=guild.id,
            config_type=GuildLoggingConfig,
            channel_type=ChannelType.LOGGING_CLANS,
        )

        clans_access_roles_ids = await get_specified_field(
            session,
            guild_id=guild.id,
            config_type=GuildClansConfig,
            field_name="clans_access_roles_ids",
        )
        if not clans_access_roles_ids:
            outcome = "clans_access_not_configured"

        if not has_any_role_from_sequence(
            cast(Member, interaction.user),
            clans_access_roles_ids,
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
                    clan = await get_clan_by_name(
                        session=session,
                        guild_id=guild.id,
                        clan_name=shop_order.payload.get("clan_name"),  # type: ignore
                        for_update=True,
                    )
                    if not clan:
                        outcome = "clan_not_found"
                    else:
                        if clan.coins < shop_order.payload.get("cost"):  # type: ignore
                            outcome = "insufficient_funds"
                        else:
                            clan.coins -= shop_order.payload.get("cost")  # type: ignore
                            shop_order.state = ShopOrderStateEnum.APPROVED  # type: ignore
                            outcome = "success"

                            await session.delete(shop_order)

    if outcome == "missing_permissions":
        await interaction.response.send_message(
            view=MissingPermissionsViewV2(),
            ephemeral=True,
        )
        return

    if outcome == "clans_access_not_configured":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка одобрения покупки",
                "Роли с доступом к кланам не настроены.",
            )
        )
        return

    if outcome == "order_not_found":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка одобрения покупки",
                "Заказ не найден в базе данных.",
            )
        )
        return

    elif outcome == "invalid_state":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка одобрения покупки",
                "Заказ уже был обработан ранее.",
            )
        )

    elif outcome == "clan_not_found":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка одобрения покупки",
                "Клан не найден в базе данных.",
            )
        )
        return

    elif outcome == "insufficient_funds":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка одобрения покупки",
                "Недостаточно средств на балансе клана.",
            )
        )
        return

    elif outcome == "success":
        assert shop_order is not None

        await interaction.followup.send(
            view=SuccessViewV2(
                "Покупка одобрена",
                f"Покупка товара **{shop_order.payload.get('item')}** для клана "  # noqa: E501
                f"**{shop_order.payload.get('clan_name')}** была успешно одобрена.",  # noqa: E501
            ),
            ephemeral=False,
        )

        view = ClanShopViewV2(
            ping_roles_ids=None,
            user_id=shop_order.user_id,
            clan_name=shop_order.payload.get("clan_name"),
            clan_balance_before=shop_order.payload.get("balance_before"),
            clan_balance_after=shop_order.payload.get("balance_after"),
            item_name=shop_order.payload.get("item"),
            item_cost=shop_order.payload.get("cost"),
            disable_buttons=True,
        )

        try:
            await message.edit(view=view)
            await thread.edit(archived=True, locked=True)
        except Exception as e:
            logger.error(
                "[clans] Error occurred while editing message and thread: %s",
                e,
            )
            return

        bot.dispatch(
            "clan_shop_order_notify",
            dto=ClanShopOrderNotifyDTO(
                guild=guild,
                event_type="clan_shop_order_notify",
                user_id=shop_order.user_id,
                moderator_id=interaction.user.id,
                state=ShopOrderStateEnum.APPROVED,
                clan_name=shop_order.payload.get("clan_name"),  # type: ignore
                item_name=shop_order.payload.get("item"),
                item_cost=shop_order.payload.get("cost"),
                clan_balance_before=shop_order.payload.get("balance_before"),
                clan_balance_after=shop_order.payload.get("balance_after"),
                custom_id=thread.id,
                logging_webhook=clans_logging_webhook,
                notifications_webhook=nightcore_notifications_webhook,  # type: ignore
            ),
        )
