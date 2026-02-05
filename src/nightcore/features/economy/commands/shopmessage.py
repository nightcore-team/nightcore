"""Command to send shop view component."""

import logging
import time
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, SelectOption, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig
from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.components.embed.success import SuccessMoveEmbed
from src.nightcore.features.economy.components.v2 import CoinsShopViewV2
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


class ShopMessage(Cog):
    def __init__(self, bot: "Nightcore"):
        self.bot = bot

    @app_commands.command(  # type: ignore
        name="shopmessage",
        description="Отправить компонент магазина.",
    )
    @app_commands.guild_only()
    @check_required_permissions(PermissionsFlagEnum.ECONOMY_ACCESS)  # type: ignore
    async def shopmessage(self, interaction: Interaction["Nightcore"]):
        """Send shop view."""

        guild = cast(Guild, interaction.guild)
        member = cast(Member, interaction.user)

        outcome = ""
        shop_items: dict[str, int] = {}

        async with specified_guild_config(
            self.bot, guild.id, config_type=GuildEconomyConfig
        ) as (guild_config, _):
            coin_name = guild_config.coin_name
            if not coin_name:
                outcome = "coin_name_not_configured"
            else:
                if not outcome:
                    outcome = "success"
                    shop_items: dict[str, int] = (
                        guild_config.economy_shop_items
                    )

        answer_time = time.perf_counter()

        if outcome == "coin_name_not_configured":
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка отправки сообщения магазина",
                    "Название коина не настроено на этом сервере.",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "success":
            if not shop_items:
                return await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Ошибка отправки сообщения магазина",
                        "В магазине нет доступных товаров.",
                        self.bot.user.display_name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            options: list[SelectOption] = [
                SelectOption(
                    label=item,
                    value=f"{item},{price}",
                )
                for item, price in shop_items.items()
            ]

            view = CoinsShopViewV2(
                self.bot,
                guild_name=guild.name,
                coin_name=cast(str, coin_name),
                shop_items=shop_items,
                options=options,
            )

            answer_end_time = time.perf_counter()

            logger.info(
                "[shopmessage] Shopmessage command took %.4f seconds",
                answer_end_time - answer_time,
            )

            start_time = time.perf_counter()
            await interaction.channel.send(view=view)  # type: ignore

            await interaction.response.send_message(
                embed=SuccessMoveEmbed(
                    "Отправка магазина",
                    "Сообщение магазина успешно отправлено.",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

            end_time = time.perf_counter()
            logger.info(
                "[shopmessage] Sending info response shop message message took %.4f seconds",  # noqa: E501
                end_time - start_time,
            )

        logger.info(
            "[command] - invoked user=%s guild=%s",
            member.id,
            guild.id,
        )


async def setup(bot: "Nightcore") -> None:
    """Setup the ShopMessage cog."""
    await bot.add_cog(ShopMessage(bot))
