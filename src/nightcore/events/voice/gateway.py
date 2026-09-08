"""Check member`s voice state and call appropriate handlers."""

import logging
from typing import cast

import discord
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildLoggingConfig, GuildPrivateChannelsConfig
from src.infra.db.models.private_rooms import PrivateRoomState
from src.infra.db.operations import (
    get_private_room_state_by_channel,
    get_specified_channel,
    get_specified_webhook,
)
from src.nightcore.bot import Nightcore
from src.utils._enums import ChannelType

logger = logging.getLogger(__name__)


class VoiceStateUpdateEvent(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        """Handle voice state update events."""
        self.bot.dispatch("count_voice_activity", member, before, after)

        try:
            # user joined a voice channel
            if before.channel is None and after.channel is not None:
                await self._handle_join(member, after)

            # user left a voice channel
            elif before.channel is not None and after.channel is None:
                await self._handle_leave(member, before)

            # user switched between channels
            elif (
                before.channel is not None
                and after.channel is not None
                and before.channel.id != after.channel.id
            ):
                await self._handle_switch(member, before, after)

        except Exception as e:
            logger.error(
                "[voice] Failed to handle voice state update event: %s",
                e,
            )

    async def _handle_join(
        self, member: discord.Member, after: discord.VoiceState
    ):
        """Handle a member joining a voice channel from nowhere."""
        guild = member.guild
        after_channel = cast(discord.VoiceChannel, after.channel)

        async with self.bot.uow.start() as session:
            create_channel_id = await get_specified_channel(
                session,
                guild_id=guild.id,
                config_type=GuildPrivateChannelsConfig,
                channel_type=ChannelType.CREATE_PRIVATE_VOICE_CHANNEL,
            )
            logging_webhook = await get_specified_webhook(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_VOICES,
            )

        self.bot.dispatch("voice_channel_join", member, after, logging_webhook)

        if create_channel_id and after_channel.id == create_channel_id:
            self.bot.dispatch("create_private_room", member, after_channel)

        logger.info(
            "[voice/join] %s joined voice channel %s",
            member,
            after_channel.name,
        )

    async def _handle_leave(
        self, member: discord.Member, before: discord.VoiceState
    ):
        """Handle a member disconnecting from a voice channel."""
        guild = member.guild
        before_channel = cast(discord.VoiceChannel, before.channel)

        async with self.bot.uow.start() as session:
            private_room_state = await get_private_room_state_by_channel(
                session, channel_id=before_channel.id, for_update=True
            )
            logging_webhook = await get_specified_webhook(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_VOICES,
            )

        self.bot.dispatch(
            "voice_channel_leave", member, before, logging_webhook
        )

        # the room belongs to the channel, so it lives until it is empty
        if private_room_state and not before_channel.members:
            self.bot.dispatch(
                "delete_private_room",
                member,
                before_channel,
                private_room_state,
            )
            logger.info(
                "[voice] Private room %s is empty; scheduled delete",
                before_channel.name,
            )

        logger.info(
            "[voice/leave] %s left voice channel %s",
            member,
            before_channel.name,
        )

    async def _handle_switch(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        """Handle a member moving between two voice channels."""
        guild = member.guild
        before_channel = cast(discord.VoiceChannel, before.channel)
        after_channel = cast(discord.VoiceChannel, after.channel)

        async with self.bot.uow.start() as session:
            private_room_state = await get_private_room_state_by_channel(
                session, channel_id=before_channel.id, for_update=True
            )
            create_channel_id = await get_specified_channel(
                session,
                guild_id=guild.id,
                config_type=GuildPrivateChannelsConfig,
                channel_type=ChannelType.CREATE_PRIVATE_VOICE_CHANNEL,
            )
            logging_webhook = await get_specified_webhook(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_VOICES,
            )

        self.bot.dispatch(
            "voice_channel_switch", member, before, after, logging_webhook
        )

        logger.info(
            "[voice] %s switched voice channel from %s to %s",
            member,
            before_channel.name,
            after_channel.name,
        )

        entering_create_channel = (
            create_channel_id is not None
            and after_channel.id == create_channel_id
        )

        # the owner of the room they just left re-entered the create-channel:
        # there is nothing to create, put them back instead
        if (
            entering_create_channel
            and private_room_state
            and private_room_state.user_id == member.id
        ):
            await self._return_to_own_room(
                member, before_channel, private_room_state
            )
            return

        if entering_create_channel:
            self.bot.dispatch("create_private_room", member, after_channel)
            logger.info(
                "[voice] %s switched to create-private channel %s; "
                "scheduled create",
                member,
                after_channel.name,
            )

        if private_room_state and not before_channel.members:
            self.bot.dispatch(
                "delete_private_room",
                member,
                before_channel,
                private_room_state,
            )
            logger.info(
                "[voice] Private room %s is empty; scheduled delete",
                before_channel.name,
            )

    async def _return_to_own_room(
        self,
        member: discord.Member,
        before_channel: discord.VoiceChannel,
        private_room_state: PrivateRoomState,
    ):
        """Move a room owner back out of the create-private channel."""
        logger.info(
            "[voice] %s already owns private room %s, moving back",
            member,
            before_channel.name,
        )

        try:
            await member.move_to(before_channel)
        except Exception as e:
            logger.error(
                "Error moving %s back to %s: %s",
                member,
                before_channel.name,
                e,
            )
            if not before_channel.members:
                self.bot.dispatch(
                    "delete_private_room",
                    member,
                    before_channel,
                    private_room_state,
                )
            try:
                await member.move_to(None)
            except Exception as e:
                logger.error("Error moving %s to None: %s", member, e)


async def setup(bot: Nightcore):
    """Setup the VoiceStateUpdateEvent cog."""
    await bot.add_cog(VoiceStateUpdateEvent(bot))
