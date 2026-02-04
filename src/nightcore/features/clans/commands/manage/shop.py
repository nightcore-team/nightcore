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
from src.infra.db.models._enums import ClanMemberRoleEnum, ShopOrderStateEnum
from src.infra.db.operations import get_clan_member, get_specified_field
from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
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
        )
        if not clan_member or clan_member.role not in [
            ClanMemberRoleEnum.LEADER,
            ClanMemberRoleEnum.DEPUTY,
        ]:
            outcome = "missing_permissions"

        icost = guild_config.clan_shop_items.get(iname, None)
        if icost is None:
            outcome = "invalid_item"

        if not outcome:
            # get clan
            clan = cast(Clan, clan_member.clan)  # type: ignore

            if not (
                clan.coins > icost  # type: ignore
            ):  # (icost can't be None here)
                outcome = "insufficient_funds"
            else:
                outcome = "success"

    if outcome == "invalid_item":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка покупки",
                "Выбранный предмет не существует в магазине клана.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "missing_permissions":
        return await interaction.response.send_message(
            embed=MissingPermissionsEmbed(
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "insufficient_funds":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка покупки",
                "Недостаточно репутации для покупки данного предмета.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "success":
        assert clan is not None

        clan_shop_channel_id = guild_config.clan_shop_channel_id
        if not clan_shop_channel_id:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка покупки",
                    "Канал для покупок в магазине клана не настроен.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        channel = await ensure_messageable_channel_exists(
            guild, clan_shop_channel_id
        )
        if channel is None:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка покупки",
                    "Канал для покупок в магазине клана не найден.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        perms = guild.me.guild_permissions

        if not all(
            [
                perms.create_private_threads,
                perms.send_messages_in_threads,
                perms.manage_threads,
                perms.manage_roles,
            ]
        ):
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                    "У меня недостаточно прав для создания ветки с покупкой.",
                ),
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True)

        try:
            thread = await cast(TextChannel, channel).create_thread(
                name=f"{iname} | {interaction.user.id}",
            )
        except Exception as e:
            logger.exception(
                "[clans/shop] Failed to create clan shop thread: %s", e
            )
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка покупки",
                    "Не удалось создать ветку для покупки в магазине клана.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        view = ClanShopViewV2(
            bot,
            ping_roles_ids=clan_buy_ping_roles_ids,
            user_id=interaction.user.id,
            clan_name=clan.name,
            clan_role_id=clan.role_id,
            clan_balance_before=clan.coins,
            clan_balance_after=clan.coins - icost,  # type: ignore
            item_name=iname,
            item_price=icost,
        )

        try:
            async with bot.uow.start() as session:
                state = ShopOrderState(
                    custom_id=thread.id,
                    guild_id=guild.id,
                    user_id=interaction.user.id,
                    state=ShopOrderStateEnum.PENDING,
                )
                session.add(state)
        except Exception as e:
            logger.exception(
                "[clans/shop] Failed to create shop order state: %s", e
            )
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка покупки",
                    "Не удалось создать состояние заказа в базе данных.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        try:
            message, _ = await asyncio.gather(
                thread.send(view=view.make_component()),
                interaction.followup.send(
                    f"Ваш запрос на покупку был успешно создан: {thread.jump_url}",  # noqa: E501
                    ephemeral=True,
                ),
            )
        except Exception as e:
            logger.exception(
                "[clans/shop] Failed to send clan shop message: %s", e
            )
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка покупки",
                    "Не удалось отправить сообщение с покупкой в магазине клана.",  # noqa: E501
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        view.custom_id = state.custom_id

        asyncio.create_task(message.edit(view=view.make_component()))

        logger.info(
            "[command] - invoked user=%s guild=%s clan_name=%s item=%s clan_balance_before=%s clan_balance_after=%s",  # noqa: E501
            interaction.user.id,
            guild.id,
            clan.name,
            iname,
            clan.coins,  # type: ignore
            clan.coins - icost,  # type: ignore
        )

        return
