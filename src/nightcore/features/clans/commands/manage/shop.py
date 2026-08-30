"""Clan invitation command."""

import asyncio
import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, TextChannel, app_commands
from discord.interactions import Interaction

from src.infra.db.models import (
    Clan,
    GuildClansConfig,
    ShopOrderState,
)
from src.infra.db.operations import (
    get_clan_member,
    get_clan_shop_item_by_name,
    get_specified_field,
)
from src.nightcore.components.view.v2 import (
    ErrorViewV2,
    MissingPermissionsViewV2,
)
from src.nightcore.features.clans._groups import manage as clan_manage_group
from src.nightcore.features.clans.components.v2 import ClanShopViewV2
from src.nightcore.features.clans.utils import clans_shop_autocomplete
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import ensure_messageable_channel_exists
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.utils._enums import ClanMemberRoleEnum, ShopOrderStateEnum

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


@clan_manage_group.command(  # type: ignore
    name="shop", description="Купить предмет в магазине клана."
)
@app_commands.describe(
    item="Предмет, который вы хотите купить для своего клана."
)
@app_commands.autocomplete(item=clans_shop_autocomplete)
@check_required_permissions(PermissionsFlagEnum.NONE)
async def shop(
    interaction: Interaction["Nightcore"],
    item: str,
):
    """Clan shop command."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    iname = item

    clan: Clan | None = None

    outcome = ""

    async with specified_guild_config(
        bot, guild.id, config_type=GuildClansConfig
    ) as (guild_config, session):
        # get clanmember
        clan_member = await get_clan_member(
            session,
            guild_id=guild.id,
            user_id=interaction.user.id,
            with_relations=True,
        )
        clan_buy_ping_roles_ids = await get_specified_field(
            session,
            guild_id=guild.id,
            config_type=GuildClansConfig,
            field_name="clan_buy_ping_roles_ids",
            for_update=True,
        )
        if not clan_member or clan_member.role not in [
            ClanMemberRoleEnum.LEADER,
            ClanMemberRoleEnum.DEPUTY,
        ]:
            outcome = "missing_permissions"

        selected_item = await get_clan_shop_item_by_name(
            session, guild_id=guild.id, name=iname
        )

        if selected_item is None:
            outcome = "unknown_item"

        if not outcome:
            # get clan
            clan = cast(Clan, clan_member.clan)  # type: ignore

            if not (
                clan.coins > selected_item.cost  # type: ignore
            ):  # (icost can't be None here)
                outcome = "insufficient_funds"
            else:
                outcome = "success"

    if outcome == "unknown_item":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка покупки",
                "Выбранный предмет не существует в магазине клана.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "missing_permissions":
        await interaction.response.send_message(
            view=MissingPermissionsViewV2(),
            ephemeral=True,
        )
        return

    if outcome == "insufficient_funds":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка покупки",
                "Недостаточно репутации для покупки данного предмета.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "success":
        assert clan is not None

        clan_shop_channel_id = guild_config.clan_shop_channel_id
        if not clan_shop_channel_id:
            await interaction.response.send_message(
                view=ErrorViewV2(
                    "Ошибка покупки",
                    "Канал для покупок в магазине клана не настроен.",
                ),
                ephemeral=True,
            )
            return

        channel = await ensure_messageable_channel_exists(
            guild, clan_shop_channel_id
        )
        if channel is None:
            await interaction.response.send_message(
                view=ErrorViewV2(
                    "Ошибка покупки",
                    "Канал для покупок в магазине клана не найден.",
                ),
                ephemeral=True,
            )
            return

        perms = guild.me.guild_permissions

        if not all(
            [
                perms.create_private_threads,
                perms.send_messages_in_threads,
                perms.manage_threads,
                perms.manage_roles,
            ]
        ):
            await interaction.response.send_message(
                view=MissingPermissionsViewV2(
                    "У меня недостаточно прав для создания ветки с покупкой."
                ),
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            thread = await cast(TextChannel, channel).create_thread(
                name=f"{iname} | {interaction.user.id}",
            )
        except Exception as e:
            logger.exception(
                "[clans/shop] Failed to create clan shop thread: %s", e
            )
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Ошибка покупки",
                    "Не удалось создать ветку для покупки в магазине клана.",
                ),
                ephemeral=True,
            )
            return

        view = ClanShopViewV2(
            ping_roles_ids=clan_buy_ping_roles_ids,
            user_id=interaction.user.id,
            clan_name=clan.name,
            clan_balance_before=clan.coins,
            clan_balance_after=clan.coins - selected_item.cost,  # type: ignore
            item_name=iname,
            item_cost=selected_item.cost,  # type: ignore
        )

        try:
            async with bot.uow.start() as session:
                state = ShopOrderState(
                    custom_id=thread.id,
                    guild_id=guild.id,
                    user_id=interaction.user.id,
                    state=ShopOrderStateEnum.PENDING,
                    payload={
                        "user_id": interaction.user.id,
                        "cost": selected_item.cost,  # type: ignore
                        "item": iname,
                        "balance_before": clan.coins,
                        "balance_after": clan.coins - selected_item.cost,  # type: ignore
                        "clan_name": clan.name,
                    },
                )
                session.add(state)

        except Exception as e:
            logger.exception(
                "[clans/shop] Failed to create shop order state: %s", e
            )
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Ошибка покупки",
                    "Не удалось создать состояние заказа в базе данных.",
                ),
                ephemeral=True,
            )
            return

        try:
            await asyncio.gather(
                thread.send(view=view),
                interaction.followup.send(
                    f"Ваш запрос на покупку был успешно создан: {thread.jump_url}",  # noqa: E501
                    ephemeral=True,
                ),
            )
        except Exception as e:
            logger.exception(
                "[clans/shop] Failed to send clan shop message: %s", e
            )
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Ошибка покупки",
                    "Не удалось отправить сообщение с покупкой в магазине клана.",  # noqa: E501
                ),
                ephemeral=True,
            )
            return

        logger.info(
            "[command] - invoked user=%s guild=%s clan_name=%s item=%s clan_balance_before=%s clan_balance_after=%s",  # noqa: E501
            interaction.user.id,
            guild.id,
            clan.name,
            iname,
            clan.coins,  # type: ignore
            clan.coins - selected_item.cost,  # type: ignore
        )

        return
