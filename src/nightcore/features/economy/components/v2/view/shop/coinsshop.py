"""Coins shop view v2 component."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self, cast

from discord import (
    Guild,
    SelectOption,
    TextChannel,
)
from discord.interactions import Interaction
from discord.ui import (
    ActionRow,
    Container,
    LayoutView,
    Select,
    Separator,
    TextDisplay,
)

from src.infra.db.models import (
    GuildEconomyConfig,
    ShopOrderState,
)
from src.infra.db.models._enums import ShopOrderStateEnum
from src.infra.db.operations import get_or_create_user, get_specified_field
from src.nightcore.components.embed import ErrorEmbed, MissingPermissionsEmbed
from src.nightcore.services.config import specified_guild_config

from .order import CoinsShopOrderViewV2

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import discord_ts, ensure_messageable_channel_exists

logger = logging.getLogger(__name__)


class SelectItemActionRow(ActionRow["CoinsShopViewV2"]):
    def __init__(self, options: list[SelectOption]):
        super().__init__()

        select = Select["CoinsShopViewV2"](
            custom_id="shopcoins:select_item",
            placeholder="Выберите товар для покупки",
            min_values=1,
            max_values=1,
            options=options,
        )

        select.callback = self.select_item_callback

        self.add_item(select)

    async def select_item_callback(
        self, interaction: Interaction["Nightcore"]
    ):
        """Handle item selection from shop."""

        selected_item = interaction.data.get("values", [])[0]  # type: ignore
        item, price = selected_item.split(",")
        guild = cast(Guild, interaction.guild)
        view = cast("CoinsShopViewV2", self.view)
        bot = interaction.client

        await interaction.response.defer(ephemeral=True)

        outcome = ""
        async with specified_guild_config(
            bot, guild.id, GuildEconomyConfig
        ) as (guild_config, session):
            shop_items = guild_config.economy_shop_items
            coin_name = guild_config.coin_name

            buyer, created = await get_or_create_user(
                session,
                guild_id=guild.id,
                user_id=interaction.user.id,
            )
            if created:
                outcome = "insufficient_funds"
            else:
                ping_roles_ids = await get_specified_field(
                    session,
                    guild_id=guild.id,
                    config_type=GuildEconomyConfig,
                    field_name="economy_shop_buy_ping_roles_ids",
                )

                if not outcome:
                    if not (buyer.coins > float(price)):
                        outcome = "insufficient_funds"
                    else:
                        outcome = "success"

        if outcome == "insufficient_funds":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка покупки товара",
                    "У вас недостаточно средств для покупки этого товара.",  # noqa: RUF001
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "success":
            economy_shop_channel_id = guild_config.economy_shop_channel_id
            if not economy_shop_channel_id:
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Ошибка покупки",
                        "Канал для покупок в магазине экономики не настроен.",
                        bot.user.display_name,  # type: ignore
                        bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            channel = await ensure_messageable_channel_exists(
                guild, economy_shop_channel_id
            )
            if channel is None:
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Ошибка покупки",
                        "Канал для покупок в магазине экономики не найден.",
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
                return await interaction.followup.send(
                    embed=MissingPermissionsEmbed(
                        bot.user.display_name,  # type: ignore
                        bot.user.display_avatar.url,  # type: ignore
                        "У меня недостаточно прав для создания ветки с покупкой.",  # noqa: E501, RUF001
                    ),
                    ephemeral=True,
                )

            try:
                thread = await cast(TextChannel, channel).create_thread(
                    name=f"{item} | {interaction.user.id}",
                )
            except Exception as e:
                logger.exception(
                    "[economy/shop] Failed to create economy shop thread: %s",
                    e,
                )
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Ошибка покупки",
                        "Не удалось создать ветку для покупки в магазине экономики.",  # noqa: E501, RUF001
                        bot.user.display_name,  # type: ignore
                        bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            oview = CoinsShopOrderViewV2(
                bot,
                ping_roles_ids=ping_roles_ids,  # type: ignore
                user_id=interaction.user.id,
                user_balance_before=buyer.coins,
                user_balance_after=buyer.coins - float(price),
                item_name=item,
                item_price=float(price),
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
                        "Не удалось создать состояние заказа в базе данных.",  # noqa: RUF001
                        bot.user.display_name,  # type: ignore
                        bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            try:
                message, _ = await asyncio.gather(
                    thread.send(view=oview.make_component()),
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
                        "Не удалось отправить сообщение с покупкой в магазине клана.",  # noqa: E501, RUF001
                        bot.user.display_name,  # type: ignore
                        bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            oview.custom_id = state.custom_id

            asyncio.create_task(  # noqa: RUF006
                message.edit(view=oview.make_component())
            )

        options = [
            SelectOption(
                label=item,
                description=f"Цена: {price:.0f} {coin_name}",
                value=f"{item},{price}",
            )
            for item, price in shop_items.items()
        ]

        view = CoinsShopViewV2(bot, guild.name, coin_name, shop_items, options)

        asyncio.create_task(interaction.message.edit(view=view))  # type: ignore  # noqa: RUF006


class CoinsShopViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        guild_name: str | None = None,
        coin_name: str | None = None,
        shop_items: dict[str, float] | None = None,
        options: list[SelectOption] | None = None,
    ):
        super().__init__(timeout=None)
        self.bot = bot

        """Build shop view component."""
        self.clear_items()

        container = Container[Self]()
        container.add_item(
            TextDisplay[Self](
                f"## <:241508crown:1430227486545018961> Магазин сервера {guild_name}"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self](
                "**Приветствую вас, уважаемые пользователи.**\n"
                "Это магазин нашего дискорд сервера.\n"
                f"Вы можете приобрести различные привилегии за **{coin_name}** <:278957bluefire:1430228112049705060>"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        if shop_items:
            for item, price in shop_items.items():
                container.add_item(
                    TextDisplay[Self](
                        f"**{item}**\n> Цена: **{int(price):.0f} {coin_name}**\n"  # noqa: E501
                    )
                )
                container.add_item(Separator[Self]())

        container.add_item(
            SelectItemActionRow(options=cast(list[SelectOption], options))
        )
        container.add_item(Separator[Self]())

        now = datetime.now(timezone.utc)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)
