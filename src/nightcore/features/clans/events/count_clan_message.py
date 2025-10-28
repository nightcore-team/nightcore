"""Count clan message event handler."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, Message
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import ClanMember, GuildClansConfig
from src.infra.db.operations import get_clan_member
from src.nightcore.features.economy.utils import (
    calculate_clan_exp_to_level,
)
from src.nightcore.services.config import specified_guild_config

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class CountClanMessageEvent(Cog):
    def __init__(self, bot: "Nightcore"):
        self.bot = bot

    @Cog.listener()
    async def on_count_clan_message(self, message: Message):
        """Handle count clan message events for clans."""

        guild = cast(Guild, message.guild)
        author = cast(Member, message.author)

        async with specified_guild_config(
            self.bot, guild.id, config_type=GuildClansConfig
        ) as (guild_config, session):
            user = cast(
                ClanMember,
                await get_clan_member(
                    session,
                    guild_id=guild.id,
                    user_id=author.id,
                    with_relations=True,
                ),
            )

            clan = user.clan

            exp_multiplier = guild_config.clan_reputation_per_message
            new_current_exp = clan.current_exp + exp_multiplier

            if new_current_exp >= clan.exp_to_level:
                new_level = clan.level + 1
                new_exp_to_level = calculate_clan_exp_to_level(new_level + 1)

                overflow_exp = new_current_exp - clan.exp_to_level

                clan.level = new_level
                clan.current_exp = overflow_exp
                clan.exp_to_level = new_exp_to_level

                logger.info(
                    "[clans/economy] Clan %s (role_id: %s) leveled up to %s in guild %s",  # noqa: E501
                    clan.name,
                    clan.role_id,
                    new_level,
                    guild.id,
                )

            else:
                clan.current_exp = new_current_exp


async def setup(bot: "Nightcore") -> None:
    """Setup the CountClanMessageEvent cog."""
    await bot.add_cog(CountClanMessageEvent(bot))
