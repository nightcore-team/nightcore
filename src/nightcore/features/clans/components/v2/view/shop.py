"""Clan shop view."""

import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self, cast

from discord import ButtonStyle, Guild, Member, Message, Thread
from discord import Container as ContainerOverride
from discord.interactions import Interaction
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    Separator,
    TextDisplay,
    button,
)

from src.infra.db.models import (
    GuildClansConfig,
    GuildLoggingConfig,
    GuildNotificationsConfig,
)
from src.infra.db.models._enums import ChannelType, ShopOrderStateEnum
from src.infra.db.operations import (
    get_clan_by_name,
    get_shop_order_state,
    get_specified_channel,
    get_specified_field,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessDeniedEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.features.clans.events.dto import (
    ClanShopOrderNotifyDTO,
)
from src.nightcore.utils import discord_ts, has_any_role_from_sequence
from src.nightcore.utils.types import MessageComponentType

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


class ClanShopActionRow(ActionRow["ClanShopViewV2"]):
    """Clan shop action row."""

    @button(
        label="Одобрить",
        style=ButtonStyle.success,
        emoji="<:52104checkmark:1414732973005340672>",
        custom_id="clan_shop:approve",
    )
    async def approve(
        self,
        interaction: Interaction,
        button: Button["ClanShopViewV2"],
    ):
        """Approve shop request button."""
        view = cast("ClanShopViewV2", self.view)
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

            clans_logging_channel_id = await get_specified_channel(
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
                outcome = "rules_channel_not_configured"

            if not has_any_role_from_sequence(
                cast(Member, interaction.user),
                clans_access_roles_ids,
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
                        clan = await get_clan_by_name(
                            session=session,
                            guild_id=guild.id,
                            clan_name=view.clan_name,  # type: ignore
                        )
                        if not clan:
                            outcome = "clan_not_found"
                        else:
                            if clan.coins < view.item_price:  # type: ignore
                                outcome = "insufficient_funds"
                            else:
                                clan.coins -= view.item_price  # type: ignore
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

        if outcome == "rules_channel_not_configured":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка одобрения покупки",
                    "Канал с правилами не настроен.",  # noqa: RUF001
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                )
            )

        if outcome == "order_not_found":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка одобрения покупки",
                    "Заказ не найден в базе данных.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                )
            )

        if outcome == "invalid_state":
            await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка одобрения покупки",
                    "Заказ уже был обработан ранее.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                )
            )

        if outcome == "clan_not_found":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка одобрения покупки",
                    "Клан не найден в базе данных.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                )
            )

        if outcome == "insufficient_funds":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка одобрения покупки",
                    "Недостаточно средств на балансе клана.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                )
            )

        if outcome == "success":
            await interaction.followup.send(
                embed=SuccessMoveEmbed(
                    "Покупка одобрена",
                    f"Покупка товара **{view.item_name}** для клана "
                    f"**{view.clan_name}** была успешно одобрена.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                )
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
            "clan_shop_order_notify",
            dto=ClanShopOrderNotifyDTO(
                guild=guild,
                event_type="clan_shop_order_notify",
                user_id=cast(int, view.user_id),
                moderator_id=interaction.user.id,
                state=ShopOrderStateEnum.APPROVED,
                clan_name=cast(str, view.clan_name),
                item_name=cast(str, view.item_name),
                item_price=cast(float, view.item_price),
                clan_balance_before=cast(float, view.clan_balance_before),
                clan_balance_after=cast(float, view.clan_balance_after),
                custom_id=cast(int, view.custom_id),
                logging_channel_id=clans_logging_channel_id,
                notifications_channel_id=nightcore_notifications_channel_id,  # type: ignore
            ),
        )

    @button(
        label="Отклонить",
        style=ButtonStyle.danger,
        emoji="<:9349_nope:1414732960841859182>",
        custom_id="clan_shop:decline",
    )
    async def decline(
        self,
        interaction: Interaction,
        button: Button["ClanShopViewV2"],
    ):
        """Decline shop request button."""

        view = cast("ClanShopViewV2", self.view)
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

            clans_loggings_channel_id = await get_specified_channel(
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

        if outcome == "clans_access_not_configured":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка отклонения покупки",
                    "Роли с доступом к кланам не настроены.",  # noqa: RUF001
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                )
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
                embed=SuccessDeniedEmbed(
                    "Покупка отклонена",
                    f"Покупка товара **{view.item_name}** для клана "
                    f"**{view.clan_name}** была отклонена.",
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
                "clan_shop_order_notify",
                dto=ClanShopOrderNotifyDTO(
                    guild=guild,
                    event_type="clan_shop_order_notify",
                    user_id=cast(int, view.user_id),
                    moderator_id=interaction.user.id,
                    state=ShopOrderStateEnum.DENIED,
                    clan_name=cast(str, view.clan_name),
                    item_name=cast(str, view.item_name),
                    item_price=cast(float, view.item_price),
                    clan_balance_before=cast(float, view.clan_balance_before),
                    clan_balance_after=cast(float, view.clan_balance_after),
                    custom_id=cast(int, view.custom_id),
                    logging_channel_id=clans_loggings_channel_id,
                    notifications_channel_id=nightcore_notifications_channel_id,  # type: ignore
                ),
            )


class ClanShopViewV2(LayoutView):
    """Clan shop view v2."""

    def __init__(
        self,
        bot: "Nightcore",
        ping_roles_ids: list[int] | None = None,
        user_id: int | None = None,
        clan_name: str | None = None,
        clan_role_id: int | None = None,
        clan_balance_before: float | None = None,
        clan_balance_after: float | None = None,
        item_name: str | None = None,
        item_price: float | None = None,
        custom_id: str | None = None,
        _build: bool = False,
    ) -> None:
        super().__init__(timeout=None)

        self.bot = bot
        self.ping_roles_ids = ping_roles_ids or []
        self.user_id = user_id
        self.clan_name = clan_name
        self.clan_role_id = clan_role_id
        self.clan_balance_before = clan_balance_before
        self.clan_balance_after = clan_balance_after
        self.item_name = item_name
        self.item_price = item_price
        self.custom_id = custom_id

        self.actions = ClanShopActionRow()

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

        main_pattern = re.compile(
            r"> Пользователь:\s*<@(\d+)>\s*\(`(\d+)`\)\s*\n"
            r"> Клан:\s*\*\*(.+?)\*\*\s*\(<@&(\d+)>\)\s*\n"
            r"> Баланс клана \(до\):\s*\*\*(\d+(?:\.\d+)?)\*\*\s*\n"
            r"> Баланс клана \(после\):\s*\*\*(\d+(?:\.\d+)?)\*\*\s*\n"
            r"> Товар:\s*\*\*(.+?)\*\*\s*\n"
            r"> Цена:\s*\*\*(\d+(?:\.\d+)?)\*\*\s*\n"
            r"> Идентификатор покупки:\s*\*\*([0-9a-fA-F\-]+)\*\*"
        )

        for component in components:
            if isinstance(component, ContainerOverride):
                for item in component.children:
                    if item.id == 2:  # type: ignore
                        logger.info(
                            "Parsing leadership roles IDs: %s",
                            item.content,  # type: ignore
                        )
                        content = item.content  # type: ignore
                        self.ping_roles_ids = [
                            int(rid)
                            for rid in roles_pattern.findall(content)  # type: ignore
                        ]
                    if item.id == 7:  # type: ignore
                        content = item.content  # type: ignore

                        try:
                            match = main_pattern.search(str(content))  # type: ignore
                            logger.info("Parsed shop view data: %s", match)

                            if not match:
                                logger.error("Content to parse: %r", content)  # type: ignore
                                raise ValueError(
                                    "Failed to parse main component data."
                                )
                        except Exception as e:
                            raise e

                        self.user_id = int(match.group(1))
                        self.clan_name = match.group(3)
                        self.clan_role_id = int(match.group(4))
                        self.clan_balance_before = float(match.group(5))
                        self.clan_balance_after = float(match.group(6))
                        self.item_name = match.group(7)
                        self.item_price = float(match.group(8))
                        self.custom_id = int(match.group(9))

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
                f"> Клан: **{self.clan_name}** (<@&{self.clan_role_id}>)\n"
                f"> Баланс клана (до): **{self.clan_balance_before}**\n"
                f"> Баланс клана (после): **{self.clan_balance_after}**\n"
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


class ShopNotifyViewV2(LayoutView):
    """Shop notify view v2."""

    def __init__(
        self,
        bot: "Nightcore",
        state: ShopOrderStateEnum,
        moderator_id: int,
        clan_name: str,
        clan_balance_before: float,
        clan_balance_after: float,
        item_name: str,
        item_price: float,
        custom_id: int,
    ) -> None:
        super().__init__(timeout=None)
        self.bot = bot

        container = Container[Self]()

        container.add_item(
            TextDisplay[Self](
                "## <:9183shoppingcart:1431625159235731516> Уведомление о покупке товара"  # noqa: E501, RUF001
            )
        )
        container.add_item(Separator[Self]())

        description = ""
        if state == ShopOrderStateEnum.APPROVED:
            description = (
                f"<@{moderator_id}> одобрил(а) вашу покупку в магазине."  # noqa: RUF001
            )
        elif state == ShopOrderStateEnum.DENIED:
            description = (
                f"<@{moderator_id}> отклонил(а) вашу покупку в магазине."  # noqa: RUF001
            )

        container.add_item(TextDisplay[Self](f"{description}"))
        container.add_item(Separator[Self]())

        container.add_item(TextDisplay[Self]("### Информация о покупке:"))  # noqa: RUF001

        container.add_item(
            TextDisplay[Self](
                f"> Клан: **{clan_name}**\n"
                f"> Баланс клана (до): **{clan_balance_before}**\n"
                f"> Баланс клана (после): **{clan_balance_after}**\n"
                f"> Товар: **{item_name}**\n"
                f"> Цена: **{item_price}**\n"
                f"> Идентификатор покупки: **{custom_id}**"
            )
        )
        container.add_item(Separator[Self]())

        now = datetime.now(timezone.utc)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)
