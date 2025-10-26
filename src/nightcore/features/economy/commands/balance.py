from typing import TYPE_CHECKING, cast

from discord import Guild, Member, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.operations import get_or_create_user
from src.nightcore.features.economy.components.v2 import BalanceViewV2
from src.nightcore.services.config import specified_guild_config

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class Balance(Cog):
    def __init__(self, bot: "Nightcore"):
        self.bot = bot

    @app_commands.command(name="balance", description="Check user's balance.")
    @app_commands.describe(
        user="The user to check the balance for. Defaults to yourself."
    )
    async def balance(
        self, interaction: Interaction, user: Member | None = None
    ):
        """Check user's balance."""

        guild = cast(Guild, interaction.guild)

        async with specified_guild_config(
            self.bot, guild_id=guild.id, config_type=GuildEconomyConfig
        ) as (
            guild_config,
            session,
        ):
            coin_name = guild_config.coin_name
            member = user or cast(Member, interaction.user)

            user_record, _ = await get_or_create_user(
                session, guild_id=guild.id, user_id=member.id
            )

        view = BalanceViewV2(self.bot, member.id, coin_name, user_record.coins)

        await interaction.response.send_message(view=view, ephemeral=True)


async def setup(bot: "Nightcore") -> None:
    """Setup the Balance cog."""
    await bot.add_cog(Balance(bot))
