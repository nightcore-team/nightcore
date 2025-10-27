"""Coins Shop Order View V2."""

import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self, cast

from discord import ButtonStyle, Guild, Interaction, Member, Message, Thread
from discord import Container as ContainerOverride
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    Separator,
    TextDisplay,
    button,
)

from src.infra.db.models import GuildEconomyConfig, GuildNotificationsConfig
from src.infra.db.models._enums import ChannelType, ShopOrderStateEnum
from src.infra.db.operations import (
    get_or_create_user,
    get_shop_order_state,
    get_specified_channel,
    get_specified_field,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.economy.events.dto import CoinsShopOrderNotifyDTO
from src.nightcore.utils import discord_ts, has_any_role_from_sequence
from src.nightcore.utils.types import MessageComponentType

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class CoinsShopOrderActionRow(ActionRow["CoinsShopOrderViewV2"]):
    """Coins shop action row."""

    @button(
        label="Одобрить",
        style=ButtonStyle.success,
        emoji="<:52104checkmark:1414732973005340672>",
        custom_id="coins_shop:approve",
    )
    async def approve(
        self,
        interaction: Interaction,
        button: Button["CoinsShopOrderViewV2"],
    ):
        """Approve shop request button."""
        view = cast("CoinsShopOrderViewV2", self.view)
        guild = cast(Guild, interaction.guild)
        bot = view.bot

        message = cast(Message, interaction.message)
        thread = cast(Thread, interaction.channel)

        view.parse_main_component_data(components=message.components)

        outcome = ""

        await interaction.response.defer()

        async with bot.uow.start() as session:
            shop_order = await get_shop_order_state(
                session=session,
                guild_id=guild.id,
                custom_id=view.custom_id,  # type: ignore
            )

            economy_access_roles_ids = await get_specified_field(
                session,
                guild_id=guild.id,
                config_type=GuildEconomyConfig,
                field_name="economy_access_roles_ids",
            )
            if not economy_access_roles_ids:
                raise FieldNotConfiguredError("clans access")

            if not has_any_role_from_sequence(
                cast(Member, interaction.user),
                economy_access_roles_ids,
            ):
                outcome = "missing_permissions"
            else:
                nightcore_notifications_channel_id = (
                    await get_specified_channel(
                        session=session,
                        guild_id=guild.id,
                        config_type=GuildNotificationsConfig,
                        channel_type=ChannelType.NIGHTCORE_NOTIFICATIONS,
                    )
                )

                if not shop_order:
                    outcome = "order_not_found"

                if not outcome:
                    if shop_order.state != ShopOrderStateEnum.PENDING:  # type: ignore
                        outcome = "invalid_state"
                    else:
                        buyer, _ = await get_or_create_user(
                            session=session,
                            guild_id=guild.id,
                            user_id=cast(int, view.user_id),
                        )

                        if buyer.coins < view.item_price:  # type: ignore
                            outcome = "insufficient_funds"
                        else:
                            buyer.coins -= view.item_price  # type: ignore
                            shop_order.state = ShopOrderStateEnum.APPROVED  # type: ignore
                            outcome = "success"

                            await session.delete(shop_order)

        if outcome == "missing_permissions":
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "order_not_found":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка одобрения покупки",
                    "Заказ не найден в базе данных.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        elif outcome == "invalid_state":
            await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка одобрения покупки",
                    "Заказ уже был обработан ранее.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        elif outcome == "insufficient_funds":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка одобрения покупки",
                    "Недостаточно средств на балансе пользователя.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        elif outcome == "success":
            await interaction.followup.send(
                embed=SuccessMoveEmbed(
                    "Покупка одобрена",
                    f"Покупка товара **{view.item_name}** была успешно одобрена.",  # noqa: E501
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        try:
            await message.edit(view=view.make_component(disable_all=True))
            await thread.edit(archived=True, locked=True)
        except Exception as e:
            logger.error(
                "[clans] Error occurred while editing message and thread: %s",
                e,
            )
            return

        bot.dispatch(
            "coins_shop_order_notify",
            dto=CoinsShopOrderNotifyDTO(
                guild=guild,
                user_id=cast(int, view.user_id),
                moderator_id=interaction.user.id,
                state=ShopOrderStateEnum.APPROVED,
                item_name=cast(str, view.item_name),
                item_price=cast(float, view.item_price),
                user_balance_before=cast(float, view.user_balance_before),
                user_balance_after=cast(float, view.user_balance_after),
                custom_id=cast(str, view.custom_id),
                notifications_channel_id=nightcore_notifications_channel_id,  # type: ignore
            ),
        )

    @button(
        label="Отклонить",
        style=ButtonStyle.danger,
        emoji="<:9349_nope:1414732960841859182>",
        custom_id="coins_shop:decline",
    )
    async def decline(
        self,
        interaction: Interaction,
        button: Button["CoinsShopOrderViewV2"],
    ):
        """Decline shop request button."""

        view = cast("CoinsShopOrderViewV2", self.view)
        guild = cast(Guild, interaction.guild)
        bot = view.bot

        message = cast(Message, interaction.message)
        thread = cast(Thread, interaction.channel)

        view.parse_main_component_data(components=message.components)

        outcome = ""

        await interaction.response.defer()

        async with bot.uow.start() as session:
            shop_order = await get_shop_order_state(
                session=session,
                guild_id=guild.id,
                custom_id=view.custom_id,  # type: ignore
            )

            economy_access_roles_ids = await get_specified_field(
                session,
                guild_id=guild.id,
                config_type=GuildEconomyConfig,
                field_name="economy_access_roles_ids",
            )
            if not economy_access_roles_ids:
                raise FieldNotConfiguredError("economy access")

            if not has_any_role_from_sequence(
                cast(Member, interaction.user),
                economy_access_roles_ids,
            ):
                outcome = "missing_permissions"
            else:
                nightcore_notifications_channel_id = (
                    await get_specified_channel(
                        session=session,
                        guild_id=guild.id,
                        config_type=GuildNotificationsConfig,
                        channel_type=ChannelType.NIGHTCORE_NOTIFICATIONS,
                    )
                )

                if not shop_order:
                    outcome = "order_not_found"

                if not outcome:
                    if shop_order.state != ShopOrderStateEnum.PENDING:  # type: ignore
                        outcome = "invalid_state"
                    else:
                        shop_order.state = ShopOrderStateEnum.DENIED  # type: ignore
                        outcome = "success"

        if outcome == "missing_permissions":
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "order_not_found":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка отклонения покупки",
                    "Заказ не найден в базе данных.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                )
            )

        elif outcome == "invalid_state":
            await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка отклонения покупки",
                    "Заказ уже был обработан ранее.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                )
            )

        elif outcome == "success":
            await interaction.followup.send(
                embed=SuccessMoveEmbed(
                    "Покупка одобрена",
                    f"Покупка товара **{view.item_name}** была отклонена.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                )
            )

            try:
                await message.edit(view=view.make_component(disable_all=True))
                await thread.edit(archived=True, locked=True)
            except Exception as e:
                logger.error(
                    "[clans] Error occurred while editing message and thread: %s",  # noqa: E501
                    e,
                )
                return

            bot.dispatch(
                "coins_shop_order_notify",
                dto=CoinsShopOrderNotifyDTO(
                    guild=guild,
                    user_id=cast(int, view.user_id),
                    moderator_id=interaction.user.id,
                    state=ShopOrderStateEnum.DENIED,
                    user_balance_before=cast(float, view.user_balance_before),
                    item_name=cast(str, view.item_name),
                    item_price=cast(float, view.item_price),
                    user_balance_after=cast(float, view.user_balance_after),
                    custom_id=cast(str, view.custom_id),
                    notifications_channel_id=nightcore_notifications_channel_id,  # type: ignore
                ),
            )


class CoinsShopOrderViewV2(LayoutView):
    """Clan shop view v2."""

    def __init__(
        self,
        bot: "Nightcore",
        ping_roles_ids: list[int] | None = None,
        user_id: int | None = None,
        user_balance_before: float | None = None,
        user_balance_after: float | None = None,
        item_name: str | None = None,
        item_price: float | None = None,
        custom_id: str | None = None,
        _build: bool = False,
    ) -> None:
        super().__init__(timeout=None)

        self.bot = bot
        self.ping_roles_ids = ping_roles_ids or []
        self.user_id = user_id
        self.user_balance_before = user_balance_before
        self.user_balance_after = user_balance_after
        self.item_name = item_name
        self.item_price = item_price
        self.custom_id = custom_id

        self.actions = CoinsShopOrderActionRow()

        if _build:
            self.make_component()

    def _disable_buttons(self):
        if self.actions:
            for item in self.actions.children:
                if isinstance(item, Button):
                    item.disabled = True

    def parse_main_component_data(
        self, components: list[MessageComponentType]
    ) -> None:
        """Parse main data from components."""

        roles_pattern = re.compile(r"<@&(\d+)>")

        pattern = re.compile(
            r"""> Пользователь: <@(?:\d+)> \(`(?P<user_id>\d+)`\)\s*"""
            r"""> Баланс пользователя \(до\): \*\*(?P<balance_before>[\d.]+)\*\*\s*"""  # noqa: E501
            r"""> Баланс пользователя \(после\): \*\*(?P<balance_after>[\d.]+)\*\*\s*"""  # noqa: E501
            r"""> Товар: \*\*(?P<item_name>[^*]+)\*\*\s*"""
            r"""> Цена: \*\*(?P<price>[\d.]+)\*\*\s*"""
            r"""> Идентификатор покупки: \*\*(?P<purchase_id>\d+)\*\*""",
            re.MULTILINE,
        )

        for component in components:
            if isinstance(component, ContainerOverride):
                for item in component.children:
                    if item.id == 2:  # type: ignore
                        content = item.content  # type: ignore
                        self.ping_roles_ids = [
                            int(rid)
                            for rid in roles_pattern.findall(content)  # type: ignore
                        ]

                    if item.id == 7:  # type: ignore
                        content = item.content  # type: ignore
                        try:
                            match = pattern.search(str(content))  # type: ignore
                            if not match:
                                raise ValueError(
                                    "No match found in the content."
                                )
                            self.user_id = int(match.group("user_id"))
                            self.user_balance_before = float(
                                match.group("balance_before")
                            )
                            self.user_balance_after = float(
                                match.group("balance_after")
                            )
                            self.item_name = match.group("item_name")
                            self.item_price = float(match.group("price"))
                            self.custom_id = int(match.group("purchase_id"))

                        except Exception as e:
                            logger.exception(
                                "[coins/shop/order] Error parsing component ID 7: %s",  # noqa: E501
                                e,
                            )
        return None

    def make_component(self, disable_all: bool = False) -> Self:
        """Create the clan shop view component."""

        self.clear_items()

        container = Container[Self]()  # 1
        container.add_item(  # 2
            TextDisplay[Self](
                f"{','.join(f'<@&{rid}>' for rid in self.ping_roles_ids)}"
            )
        )
        container.add_item(Separator[Self]())  # 3
        container.add_item(  # 4
            TextDisplay[Self](
                "## <:9183shoppingcart:1431625159235731516> Запрос на покупку товара"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())  # 5

        # 6
        container.add_item(TextDisplay[Self]("### Информация о покупке:"))  # noqa: RUF001
        # 7
        container.add_item(
            TextDisplay[Self](
                f"> Пользователь: <@{self.user_id}> (`{self.user_id}`)\n"
                f"> Баланс пользователя (до): **{self.user_balance_before}**\n"
                f"> Баланс пользователя (после): **{self.user_balance_after}**\n"  # noqa: E501
                f"> Товар: **{self.item_name}**\n"
                f"> Цена: **{self.item_price}**\n"
                f"> Идентификатор покупки: **{self.custom_id}**"
            )
        )
        # 8
        container.add_item(Separator[Self]())

        # 9 (10, 11)
        container.add_item(self.actions)
        # 12
        container.add_item(Separator[Self]())

        # 13
        container.add_item(
            TextDisplay[Self](
                "Товар будет выдан после проверки модерацией вашего запроса."
            )
        )
        # 14
        container.add_item(Separator[Self]())

        # 15
        now = datetime.now(timezone.utc)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        if disable_all:
            self._disable_buttons()

        self.add_item(container)

        return self
