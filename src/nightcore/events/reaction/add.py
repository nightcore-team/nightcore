"""Handle reaction add events."""

import logging
from typing import TYPE_CHECKING

import discord
from discord import Reaction, User
from discord.ext.commands.cog import Cog  # type: ignore

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import get_specified_channel

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import ensure_messageable_channel_exists

logger = logging.getLogger(__name__)


class ReactionAddEvent(Cog):
    def __init__(self, bot: "Nightcore"):
        self.bot = bot

    @Cog.listener()
    async def on_reaction_add(self, reaction: Reaction, user: User):
        """Handle reaction add events."""

        guild = reaction.message.guild

        if not guild:
            logger.info(
                "[reactions] - Reaction added in a non-guild context by user %s",  # noqa: E501
                user.id,
            )
            return

        async with self.bot.uow.start() as session:
            log_channel_id: int | None = await get_specified_channel(
                session,  # type: ignore
                guild_id=reaction.message.guild.id,  # type: ignore
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_REACTIONS,
            )

        if log_channel_id is None:
            logger.info(
                "[reactions] - Logging channel for reactions not configured in guild %s",  # noqa: E501
                guild.id,
            )
            return

        log_channel = await ensure_messageable_channel_exists(
            guild, log_channel_id
        )

        embed = discord.Embed(
            title="Добавлена реакция",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(
            name="Пользователь",
            value=f"{user.mention} (`{user.id}`)",
            inline=False,
        )
        embed.add_field(
            name="Сообщение",
            value=(
                f"[Перейти к сообщению]({reaction.message.jump_url}) "
                f"`({reaction.message.id})`"
            ),
            inline=False,
        )
        embed.add_field(
            name="Реакция",
            value=f"{reaction.emoji} `({reaction.emoji})`",
            inline=False,
        )
        embed.set_footer(
            text="Powered by nightcore",
            icon_url=self.bot.user.display_avatar.url,  # type: ignore
        )

        await log_channel.send(embed=embed)  # type: ignore

        logger.info(
            "[reactions] - Reaction add logged in guild %s by user %s",
            guild.id,
            user.id,
        )


async def setup(bot: "Nightcore"):
    """Setup the ReactionAddEvents cog."""
    await bot.add_cog(ReactionAddEvent(bot))
