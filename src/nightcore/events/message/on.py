"""Message events module."""

import logging
from typing import cast

import discord
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import (
    GuildLevelsConfig,
    GuildModerationConfig,
    MainGuildConfig,
)
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import (
    get_clan_member,
    get_specified_channel,
    get_specified_field,
)
from src.nightcore.bot import Nightcore
from src.nightcore.utils import has_any_role

logger = logging.getLogger(__name__)


class OnMessageEvent(Cog):
    def __init__(self, bot: Nightcore):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle message create events."""

        if message.author.bot:
            return

        guild = message.guild

        if not guild:
            if not message.attachments:
                return
            if len(message.attachments) > 1:
                return
            try:
                self.bot.dispatch("stats_provided", message)
            except Exception as e:
                logger.error("Failed to dispatch stats_provided event: %s", e)

        else:
            async with self.bot.uow.start() as session:
                proposal_channel_id = await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=MainGuildConfig,
                    channel_type=ChannelType.CREATE_PROPOSALS,
                )
                if not proposal_channel_id:
                    logger.error(
                        "[proposals] No proposal channel found for guild %s",
                        guild.id,
                    )

                count_messages_type = await get_specified_field(
                    session,
                    guild_id=guild.id,
                    config_type=GuildLevelsConfig,
                    field_name="count_messages_type",
                )

                count_messages_channel_id = await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=GuildLevelsConfig,
                    channel_type=ChannelType.COUNT_MESSAGES,
                )
                count_moderation_messages_channel_id = (
                    await get_specified_channel(
                        session,
                        guild_id=guild.id,
                        config_type=GuildModerationConfig,
                        channel_type=ChannelType.COUNT_MODERATION_MESSAGES,
                    )
                )

                trackable_moderation_role_id = await get_specified_field(
                    session,
                    guild_id=guild.id,
                    config_type=GuildModerationConfig,
                    field_name="trackable_moderation_role_id",
                )
                if not count_messages_channel_id:
                    logger.error(
                        "[levels] No count messages channel found for guild %s",  # noqa: E501
                        guild.id,
                    )

                clan_member = await get_clan_member(
                    session,
                    guild_id=guild.id,
                    user_id=message.author.id,
                )

            if message.channel.id == proposal_channel_id:
                self.bot.dispatch("create_proposal", message)
                return

            if count_messages_type == "channel_only":
                if message.channel.id == count_messages_channel_id:
                    self.bot.dispatch("count_message", message)
                if message.channel.id == count_moderation_messages_channel_id:
                    if trackable_moderation_role_id:
                        if has_any_role(
                            cast(discord.Member, message.author),
                            trackable_moderation_role_id,
                        ):
                            self.bot.dispatch(
                                "count_moderation_message", message
                            )
                    else:
                        logger.error(
                            "[moderation] No trackable moderation role set for guild %s",  # noqa: E501
                            guild.id,
                        )

            elif count_messages_type == "all":
                self.bot.dispatch("count_message", message)

                if trackable_moderation_role_id:
                    if has_any_role(
                        cast(discord.Member, message.author),
                        trackable_moderation_role_id,
                    ):
                        self.bot.dispatch("count_moderation_message", message)
                else:
                    logger.error(
                        "[moderation] No trackable moderation role set for guild %s",  # noqa: E501
                    )

            if clan_member:
                self.bot.dispatch("count_clan_message", message)

        logger.info("[message] Message received: %s", message)

        return


async def setup(bot: Nightcore) -> None:
    """Setup the OnMessageEvent cog."""
    await bot.add_cog(OnMessageEvent(bot))
