"""Handle count moderation message events."""

import logging
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, Member, Message
from discord.ext.commands import Cog  # type: ignore

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.infra.db.models.moderationmessage import ModerationMessage

logger = logging.getLogger(__name__)


class CountModerationMessageEvent(Cog):
    def __init__(self, bot: "Nightcore"):
        self.bot = bot

    @Cog.listener()
    async def on_count_moderation_message(self, message: Message):
        """Handle count moderation message events."""

        guild = cast(Guild, message.guild)
        author = cast(Member, message.author)

        async with self.bot.uow.start() as session:
            moderator_message = ModerationMessage(
                guild_id=guild.id,
                moderator_id=author.id,
                time_now=discord.utils.utcnow(),
            )

            session.add(moderator_message)

        logger.info(
            "[%s/log] - invoked user=%s guild=%s",
            "economy/levelup",
            author.id,
            guild.id,
        )


async def setup(bot: "Nightcore"):
    """Setup the CountModerationMessageEvent cog."""
    await bot.add_cog(CountModerationMessageEvent(bot))
