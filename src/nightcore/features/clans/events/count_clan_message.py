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
            _user = await get_clan_member(
                session,
                guild_id=guild.id,
                user_id=author.id,
                with_relations=True,
                for_update=True,
            )
            if _user is None:
                return
            user = cast(ClanMember, _user)

            # lock clan row explicitly for RMW on exp/level
            from src.infra.db.operations import get_clan_by_id

            clan = await get_clan_by_id(
                session,
                guild_id=guild.id,
                clan_id=user.clan.id,
                for_update=True,  # type: ignore
            )
            if clan is None:
                return

            exp_multiplier = guild_config.base_exp_multiplier
            new_current_exp = clan.current_exp + exp_multiplier

            while new_current_exp >= clan.exp_to_level:
                overflow_exp = new_current_exp - clan.exp_to_level
                clan.level += 1
                clan.exp_to_level = calculate_clan_exp_to_level(clan.level + 1)
                new_current_exp = overflow_exp

                logger.info(
                    "[clans/economy] Clan %s (role_id: %s) leveled up to %s in guild %s",  # noqa: E501
                    clan.name,
                    clan.role_id,
                    clan.level,
                    guild.id,
                )

            clan.current_exp = new_current_exp

        logger.info(
            "[%s/log] - invoked user=%s guild=%s clan=%s",
            "economy/levelup",
            author.id,
            guild.id,
            clan.id,
        )


async def setup(bot: "Nightcore") -> None:
    """Setup the CountClanMessageEvent cog."""
    await bot.add_cog(CountClanMessageEvent(bot))
