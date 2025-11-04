"""Command to send shop view component."""

import logging
import time
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, SelectOption, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig
from src.nightcore.components.embed import ErrorEmbed, MissingPermissionsEmbed
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.economy.components.v2 import CoinsShopViewV2
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import has_any_role_from_sequence

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


class ShopMessage(Cog):
    def __init__(self, bot: "Nightcore"):
        self.bot = bot

    @app_commands.command(
        name="shopmessage",
        description="Отправить компонент магазина.",
    )
    async def shopmessage(self, interaction: Interaction["Nightcore"]):
        """Send shop view."""

        guild = cast(Guild, interaction.guild)
        member = cast(Member, interaction.user)

        outcome = ""
        shop_items: dict[str, float] = {}

        async with specified_guild_config(
            self.bot, guild.id, config_type=GuildEconomyConfig
        ) as (guild_config, _):
            economy_access_roles_ids = guild_config.economy_access_roles_ids
            if not economy_access_roles_ids:
                raise FieldNotConfiguredError("economy access")

            coin_name = guild_config.coin_name
            if not coin_name:
                outcome = "coin_name_not_configured"
            else:
                if not has_any_role_from_sequence(
                    member, economy_access_roles_ids
                ):
                    outcome = "missing_permissions"

                if not outcome:
                    outcome = "success"
                    shop_items: dict[str, float] = (
                        guild_config.economy_shop_items
                    )

        answer_time = time.perf_counter()
        if outcome == "missing_permissions":
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

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
            await interaction.response.send_message(
                view=view,
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
