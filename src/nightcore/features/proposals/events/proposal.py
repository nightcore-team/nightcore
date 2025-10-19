"""Proposal creation event handler."""

import logging
from typing import cast

from discord import Guild, Message
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import MainGuildConfig
from src.nightcore.bot import Nightcore
from src.nightcore.features.proposals.components.v2 import (
    ProposalViewV2,
)
from src.nightcore.features.proposals.utils import (
    strip_discord_markdown_to_plain,
)
from src.nightcore.services.config import specified_guild_config

logger = logging.getLogger(__name__)


class CreateProposalEvent(Cog):
    def __init__(self, bot: Nightcore):
        self.bot = bot

    @Cog.listener()
    async def on_create_proposal(self, message: Message):
        """Handle create proposal event."""
        guild = cast(Guild, message.guild)
        if message.author.bot:
            return

        await message.delete()

        if not message.content and message.attachments:
            return

        async with specified_guild_config(
            self.bot, guild.id, MainGuildConfig
        ) as (guild_config, _):
            proposals_count = guild_config.proposals_count

            proposals_count, guild_config.proposals_count = (
                proposals_count + 1,
                guild_config.proposals_count + 1,
            )

        description = strip_discord_markdown_to_plain(message.content)

        view = ProposalViewV2(
            bot=self.bot,
            proposals_count=proposals_count,
            description=description,
            user_id=message.author.id,
        ).make_component()

        try:
            await message.channel.send(
                view=view,
            )
        except Exception as e:
            logger.exception(
                "Failed to send proposal message in guild %s: %s",
                guild.id,
                e,
            )


async def setup(bot: Nightcore) -> None:
    """Setup the CreateProposalEvent cog."""
    await bot.add_cog(CreateProposalEvent(bot))
