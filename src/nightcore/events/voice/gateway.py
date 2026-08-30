"""Check member`s voice state and call appropriate handlers."""

import asyncio
import logging

import discord
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildLoggingConfig, GuildPrivateChannelsConfig
from src.infra.db.operations import (
    get_private_room_state,
    get_specified_channel,
    get_specified_webhook,
)
from src.nightcore.bot import Nightcore
from src.nightcore.utils import ensure_messageable_channel_exists
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
        guild = member.guild

        try:
            self.bot.dispatch("count_voice_activity", member, before, after)

            # user joined a voice channel
            if before.channel is None and after.channel is not None:
                async with self.bot.uow.start() as session:
                    private_room_state = await get_private_room_state(
                        session, user_id=member.id, for_update=True
                    )
                    create_private_room_channel_id = (
                        await get_specified_channel(
                            session,
                            guild_id=guild.id,
                            config_type=GuildPrivateChannelsConfig,
                            channel_type=ChannelType.CREATE_PRIVATE_VOICE_CHANNEL,
                        )
                    )
                    logging_webhook = await get_specified_webhook(
                        session,
                        guild_id=guild.id,
                        config_type=GuildLoggingConfig,
                        channel_type=ChannelType.LOGGING_VOICES,
                    )

                if (
                    create_private_room_channel_id
                    and after.channel.id == create_private_room_channel_id
                ):
                    if private_room_state:
                        _ch = await ensure_messageable_channel_exists(
                            guild, private_room_state.channel_id
                        )
                        if _ch:
                            try:
                                await member.move_to(_ch)  # type: ignore
                                logger.info(
                                    "[voice] Moved %s to their existing "
                                    "private room %s",
                                    member,
                                    _ch.name,  # type: ignore[attr-defined]
                                )
                                return
                            except Exception as e:
                                logger.error(
                                    "Error moving %s to their private room "
                                    "%s: %s",
                                    member,
                                    _ch.name,  # type: ignore[attr-defined]
                                    e,
                                )
                                try:
                                    asyncio.gather(
                                        member.move_to(None),
                                        member.send(
                                            f"Произошла ошибка при "
                                            f"перемещении вас в ваш "
                                            f"приватный канал. Пожалуйста, "
                                            f"зайдите сами в "
                                            f"{_ch.mention}."  # type: ignore
                                        ),
                                    )
                                except Exception as e:
                                    logger.error(
                                        "Error moving %s to None or sending "
                                        "message: %s",
                                        member,
                                        e,
                                    )
                                return

                        else:
                            # Stale record: channel not found, delete with lock
                            async with self.bot.uow.start() as session:
                                fresh = await get_private_room_state(
                                    session,
                                    user_id=member.id,
                                    for_update=True,
                                )
                                if (
                                    fresh is not None
                                    and fresh.channel_id
                                    == private_room_state.channel_id
                                ):
                                    await session.delete(fresh)
                                    await session.flush()
                            logger.info(
                                "[voice] Private room channel %s for %s not "
                                "found, creating a new one",
                                private_room_state.channel_id,
                                member,
                            )
                    else:
                        self.bot.dispatch(
                            "create_private_room", member, after.channel
                        )
                        return

                    self.bot.dispatch(
                        "create_private_room", member, after.channel
                    )
                else:
                    try:
                        self.bot.dispatch(
                            "voice_channel_join",
                            member,
                            after,
                            logging_webhook,
                        )
                    except Exception as e:
                        logger.error(
                            "[voice/join] Error dispatching voice channel "
                            "join event: %s",
                            e,
                        )
                logger.info(
                    "[voice/join] %s joined voice channel %s",
                    member,
                    getattr(
                        after.channel,
                        "name",
                        str(getattr(after.channel, "id", "unknown")),
                    ),
                )

            # check if member left a voice channel
            elif before.channel is not None and after.channel is None:
                async with self.bot.uow.start() as session:
                    private_room_state = await get_private_room_state(
                        session, user_id=member.id, for_update=True
                    )
                    logging_webhook = await get_specified_webhook(
                        session,
                        guild_id=guild.id,
                        config_type=GuildLoggingConfig,
                        channel_type=ChannelType.LOGGING_VOICES,
                    )

                if (
                    private_room_state
                    and private_room_state.channel_id == before.channel.id
                ):
                    self.bot.dispatch(
                        "delete_private_room",
                        member,
                        before.channel,
                        private_room_state,
                    )
                else:
                    try:
                        self.bot.dispatch(
                            "voice_channel_leave",
                            member,
                            before,
                            logging_webhook,
                        )
                    except Exception as e:
                        logger.error(
                            "[voice/leave] Error dispatching voice channel "
                            "leave event: %s",
                            e,
                        )
                logger.info(
                    "[voice/leave] %s left voice channel %s",
                    member,
                    getattr(
                        before.channel,
                        "name",
                        str(getattr(before.channel, "id", "unknown")),
                    ),
                )

            # switched between channels
            elif (
                before.channel is not None
                and after.channel is not None
                and before.channel.id != after.channel.id
            ):
                async with self.bot.uow.start() as session:
                    private_room_state = await get_private_room_state(
                        session, user_id=member.id, for_update=True
                    )
                    create_private_room_channel_id = (
                        await get_specified_channel(
                            session,
                            guild_id=guild.id,
                            config_type=GuildPrivateChannelsConfig,
                            channel_type=ChannelType.CREATE_PRIVATE_VOICE_CHANNEL,
                        )
                    )
                    logging_webhook = await get_specified_webhook(
                        session,
                        guild_id=guild.id,
                        config_type=GuildLoggingConfig,
                        channel_type=ChannelType.LOGGING_VOICES,
                    )

                if (
                    private_room_state
                    and create_private_room_channel_id
                    and after.channel.id == create_private_room_channel_id
                ):
                    logger.info(
                        "[voice] %s switched to create-private channel %s, "
                        "moving back to %s",
                        member,
                        after.channel.name,
                        before.channel.name,
                    )
                    try:
                        await member.move_to(before.channel)
                    except Exception as e:
                        logger.error(
                            "Error moving %s back to %s: %s",
                            member,
                            before.channel.name,
                            e,
                        )
                        self.bot.dispatch(
                            "delete_private_room",
                            member,
                            before.channel,
                            private_room_state,
                        )
                        try:
                            await member.move_to(None)
                        except Exception as e:
                            logger.error(
                                "Error moving %s to None: %s",
                                member,
                                e,
                            )
                        return

                # if user switched from their private channel to another
                elif (
                    private_room_state
                    and before.channel
                    and before.channel.id == private_room_state.channel_id
                    and after.channel.id != private_room_state.channel_id
                ):
                    self.bot.dispatch(
                        "voice_channel_switch",
                        member,
                        before,
                        after,
                        logging_webhook,
                    )
                    self.bot.dispatch(
                        "delete_private_room",
                        member,
                        before.channel,
                        private_room_state,
                    )
                    logger.info(
                        "[voice] %s left their private channel %s -> %s; "
                        "scheduled delete",
                        member,
                        before.channel.name,
                        after.channel.name,
                    )

                elif (
                    not private_room_state
                    and create_private_room_channel_id
                    and after.channel.id == create_private_room_channel_id
                ):
                    self.bot.dispatch(
                        "voice_channel_switch",
                        member,
                        before,
                        after,
                        logging_webhook,
                    )
                    self.bot.dispatch(
                        "create_private_room", member, after.channel
                    )
                    logger.info(
                        "[voice] %s switched to create-private channel %s; "
                        "scheduled create",
                        member,
                        after.channel.name,
                    )

                # if user just switched between two non-private channels
                else:
                    self.bot.dispatch(
                        "voice_channel_switch",
                        member,
                        before,
                        after,
                        logging_webhook,
                    )
                    logger.info(
                        "[voice] %s switched voice channel from %s to %s",
                        member,
                        getattr(
                            before.channel, "name", str(before.channel.id)
                        ),
                        getattr(after.channel, "name", str(after.channel.id)),
                    )

        except Exception as e:
            logger.error(
                "[voice] Failed to dispatch voice state update event: %s",
                e,
            )


async def setup(bot: Nightcore):
    """Setup the VoiceStateUpdateEvent cog."""
    await bot.add_cog(VoiceStateUpdateEvent(bot))
