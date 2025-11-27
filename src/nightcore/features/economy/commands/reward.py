"""Command to take daily coins reward."""

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.operations import get_or_create_user
from src.nightcore.components.embed import ErrorEmbed, SuccessMoveEmbed
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import discord_ts

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


class Reward(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(
        name="reward", description="Забрать ежедневную награду."
    )  # type: ignore
    @app_commands.guild_only()
    @check_required_permissions(PermissionsFlagEnum.NONE)  # type: ignore
    async def reward(self, interaction: Interaction["Nightcore"]) -> None:
        """Claim your daily reward."""

        guild = cast(Guild, interaction.guild)

        outcome = ""

        async with specified_guild_config(
            self.bot, guild.id, config_type=GuildEconomyConfig
        ) as (guild_config, session):
            user, _ = await get_or_create_user(
                session, guild_id=guild.id, user_id=interaction.user.id
            )

            now = datetime.now(timezone.utc)

            if user.reward_time is not None:
                time_since_last_reward = now - user.reward_time

                if time_since_last_reward < timedelta(hours=24):
                    next_reward = user.reward_time + timedelta(hours=24)

                    outcome = "reward_too_early"

            if not outcome:
                reward_coins = guild_config.reward_bonus
                if not reward_coins or reward_coins <= 0:
                    outcome = "no_reward_configured"
                else:
                    coin_name = guild_config.coin_name

                    user.coins += reward_coins
                    user.reward_time = now

                    outcome = "success"

        if outcome == "no_reward_configured":
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка получения ежедневной награды",
                    "Ежедневная награда не настроена на этом сервере.",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "reward_too_early":
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка получения ежедневной награды",
                    f"Вы уже получали свою ежедневную награду. \n> Следующая награда: {discord_ts(next_reward)}",  # noqa: E501 # type: ignore
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        elif outcome == "success":
            return await interaction.response.send_message(
                embed=SuccessMoveEmbed(
                    "Успешно получена ежедневная награда",
                    f"Вы получили свою ежедневную награду: {reward_coins} {coin_name or 'коинов'}",  # type: ignore  # noqa: E501
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        logger.info(
            "[command] - invoked user=%s guild=%s",
            interaction.user.id,
            guild.id,
        )


async def setup(bot: "Nightcore") -> None:
    """Setup the Reward cog."""
    await bot.add_cog(Reward(bot))
