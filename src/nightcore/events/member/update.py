import logging

import discord
from discord.ext.commands import Cog  # type: ignore

from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class UpdateMemberHandler(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_member_update(
        self, before: discord.Member, after: discord.Member
    ):
        """Handle member update events."""
        try:
            # self.bot.dispatch("infomaker_member_update", before, after)
            self.bot.dispatch("default_member_update", before, after)
        except Exception as e:
            logger.exception(
                "[logging] Failed to dispatch member update event: %s", e
            )


async def setup(bot: Nightcore):
    """Setup the UpdateMemberHandler cog."""
    await bot.add_cog(UpdateMemberHandler(bot))
