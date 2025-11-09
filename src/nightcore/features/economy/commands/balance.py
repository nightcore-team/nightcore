"""Command to check user's balance."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, User, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.operations import get_or_create_user
from src.nightcore.features.economy.components.v2 import BalanceViewV2
from src.nightcore.services.config import specified_guild_config

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class Balance(Cog):
    def __init__(self, bot: "Nightcore"):
        self.bot = bot

    @app_commands.command(
        name="balance", description="Посмотреть баланс пользователя"
    )
    @app_commands.describe(
        user="Пользователь, чей баланс нужно проверить. По умолчанию - вы сами"
    )
    async def balance(
        self, interaction: Interaction, user: User | None = None
    ):
        """Check user's balance."""

        guild = cast(Guild, interaction.guild)

        member = user or interaction.user

        async with specified_guild_config(
            self.bot, guild_id=guild.id, config_type=GuildEconomyConfig
        ) as (
            guild_config,
            session,
        ):
            coin_name = guild_config.coin_name
            user_record, _ = await get_or_create_user(
                session, guild_id=guild.id, user_id=member.id
            )

        view = BalanceViewV2(self.bot, member.id, coin_name, user_record.coins)

        await interaction.response.send_message(view=view, ephemeral=True)

        logger.info(
            "[command] - invoked user=%s guild=%s target_user=%s",
            interaction.user.id,
            guild.id,
            member.id,
        )


async def setup(bot: "Nightcore") -> None:
    """Setup the Balance cog."""
    await bot.add_cog(Balance(bot))
