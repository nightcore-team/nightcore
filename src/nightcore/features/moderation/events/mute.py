"""Mute Events Cog for Nightcore Bot."""

import asyncio
import logging
from collections.abc import Awaitable
from datetime import timezone

import discord
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import (
    create_punish,
    create_temp_punish,
    get_latest_temp_punish,
    get_mpmute_role,
    get_mute_role,
    get_mute_type,
    get_specified_channel,
    get_vmute_role,
)
from src.nightcore.bot import Nightcore
from src.nightcore.features.moderation.events import (
    UserMutedEventData,
    UserUnmutedEventData,
)
from src.nightcore.features.moderation.utils import (
    calculate_end_time,
    send_moderation_log,
    send_punish_dm_message,
    send_unpunish_dm_message,
)
from src.nightcore.utils import discord_ts, ensure_member_exists

logger = logging.getLogger(__name__)


class UserMutedEvent(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_user_muted(
        self,
        *,
        data: UserMutedEventData,
    ) -> None:
        """Handle user punished events."""
        logger.info(
            "[event] on_user_muted - %s: Guild: %s, Member: %s, Reason: %s, Duration: %s",  # noqa: E501
            data.category,
            data.moderator.guild.id,
            data.user.id,
            data.reason,
            data.duration,
        )

        try:
            user = await self.bot.fetch_user(data.user.id)
            data.user = user
        except Exception as e:
            logger.exception(
                "[event] on_user_muted - %s: Failed to fetch user %s: %s",
                data.category,
                data.user.id,
                e,
            )
            return

        end_time = calculate_end_time(data.duration)
        data.end_time = discord_ts(end_time)

        # db insert and getting logging channel
        async with self.bot.uow.start() as session:
            try:
                punish_info = await create_punish(
                    session,
                    guild_id=data.moderator.guild.id,
                    user_id=data.user.id,
                    moderator_id=data.moderator.id,
                    category=data.category,
                    reason=data.reason,
                    duration=data.duration,
                    end_time=end_time,
                    time_now=discord.utils.utcnow().astimezone(timezone.utc),
                )
            except Exception as e:
                logger.exception(
                    "[event] on_user_muted - %s: Failed to create punish record: %s",  # noqa: E501
                    data.category,
                    e,
                )
                return

            try:
                await create_temp_punish(
                    session,
                    guild_id=data.moderator.guild.id,
                    user_id=data.user.id,
                    category=data.category,
                    end_time=end_time,
                )
            except Exception as e:
                logger.exception(
                    "[event] on_user_muted - %s: Failed to create punish record: %s",  # noqa: E501
                    data.category,
                    e,
                )
                return

            logging_channel_id = await get_specified_channel(
                session,
                guild_id=data.moderator.guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_MODERATION,
            )

        gather_list: list[Awaitable[None]] = []

        gather_list.append(
            send_punish_dm_message(self.bot, event_data=data),
        )

        # sending log message
        if logging_channel_id:
            gather_list.append(
                send_moderation_log(
                    self.bot, channel_id=logging_channel_id, event_data=data
                )
            )
        else:
            logger.warning(
                "[event] on_user_muted - %s: Guild: %s, logging channel is not set",  # noqa: E501
                data.moderator.guild.id,
                punish_info.category,
            )

        try:
            await asyncio.gather(*gather_list, return_exceptions=True)
        except Exception as e:
            logger.exception(
                "[event] on_user_muted - %s: Failed to send DM or log message: %s",  # noqa: E501
                data.category,
                e,
            )

    @Cog.listener()
    async def on_user_unmute(
        self, *, data: UserUnmutedEventData, by_command: bool = False
    ) -> None:
        """Handle user unmuted events."""
        logger.info(
            "[event] user_unmute - %s: Guild: %s, Member: %s, Reason: %s",
            data.category,
            data.guild_id,
            data.user_id,
            data.reason,
        )

        guild = self.bot.get_guild(data.guild_id)
        if guild is None:
            logger.error(
                "[event] user_unmute - %s: Guild %s not in cache",
                data.category,
                data.guild_id,
            )
            return

        # Try to get the member from the cache
        # TODO: вынести в отдельную функцию
        member = await ensure_member_exists(guild, data.user_id)
        if member is None:
            logger.error(
                "[event] user_unmute - %s: Member %s not found in guild %s",
                data.category,
                data.user_id,
                data.guild_id,
            )
            return

        async with self.bot.uow.start() as session:
            # Ensure variables are always defined
            mute_role_id: int | None = None
            mute_type: str | None = None

            match data.mute_type:
                case "default":
                    mute_type = await get_mute_type(
                        session, guild_id=data.guild_id
                    )
                    if mute_type == "role":
                        mute_role_id = await get_mute_role(
                            session, guild_id=data.guild_id
                        )
                case "mpmute":
                    mute_role_id = await get_mpmute_role(
                        session, guild_id=data.guild_id
                    )
                    mute_type = "role"  # treated as role mute
                case "vmute":
                    mute_role_id = await get_vmute_role(
                        session, guild_id=data.guild_id
                    )
                    mute_type = "role"  # treated as role mute
                case _:
                    mute_type = None

            if by_command:
                await create_punish(
                    session,
                    guild_id=data.guild_id,
                    user_id=data.user_id,
                    moderator_id=data.moderator_id,
                    category=f"un{data.category}",
                    reason=data.reason,
                    end_time=None,
                    time_now=discord.utils.utcnow().astimezone(timezone.utc),
                )

                temp = await get_latest_temp_punish(
                    session,
                    guild_id=data.guild_id,
                    user_id=data.user_id,
                    category=data.category,
                )
                if temp:
                    await session.delete(temp)

                else:
                    logger.error(
                        "[event] user_unmute - %s: No active temporary punishment found for user %s in guild %s",  # noqa: E501
                        data.category,
                        data.user_id,
                        data.guild_id,
                    )

            logging_channel_id = await get_specified_channel(
                session,
                guild_id=data.guild_id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_MODERATION,
            )

        if not by_command:
            # check if mute by role or timeout (here)
            match data.mute_type:
                case "default":
                    if mute_type == "role":
                        mrole = None
                        if mute_role_id:
                            # Try cache first
                            mrole = guild.get_role(mute_role_id)
                            if mrole is None:
                                try:
                                    mrole = await guild.fetch_role(
                                        mute_role_id
                                    )
                                except discord.NotFound:
                                    mrole = None
                                except discord.HTTPException as e:
                                    logger.exception(
                                        "[event] user_unmute - %s: Failed to fetch mute role %s in guild %s: %s",  # noqa: E501
                                        data.category,
                                        mute_role_id,
                                        data.guild_id,
                                        e,
                                    )
                                    mrole = None
                        if not mute_role_id or mrole is None:
                            logger.error(
                                "[event] user_unmute - %s: Mute role %s not found in guild %s",  # noqa: E501
                                data.category,
                                mute_role_id,
                                data.guild_id,
                            )
                        else:
                            member_roles = {r.id for r in member.roles}
                            has_role = mute_role_id in member_roles
                            if not has_role:
                                logger.error(
                                    "[event] user_unmute - %s: User %s does not have mute role %s",  # noqa: E501
                                    data.category,
                                    member.id,
                                    mute_role_id,
                                )
                            else:
                                try:
                                    await member.remove_roles(mrole)
                                except Exception as e:
                                    logger.exception(
                                        "[event] user_unmute - %s: Failed to remove mute role %s from user %s: %s",  # noqa: E501
                                        data.category,
                                        mute_role_id,
                                        member.id,
                                        e,
                                    )
                                    raise e
                    elif mute_type == "timeout":
                        if member.is_timed_out():
                            try:
                                await member.timeout(None, reason=data.reason)
                            except Exception as e:
                                logger.exception(
                                    "[event] user_unmute - %s: Failed to remove timeout from user %s: %s",  # noqa: E501
                                    data.category,
                                    member.id,
                                    e,
                                )
                        else:
                            logger.info(
                                "[event] user_unmute - %s: User %s is not timed out",  # noqa: E501
                                data.category,
                                member.id,
                            )
                    else:
                        logger.error(
                            "[event] user_unmute - %s: Unknown mute type for user %s",  # noqa: E501
                            data.category,
                            member.id,
                        )
                case "mpmute" | "vmute":
                    mrole = None
                    if mute_role_id:
                        # Try cache first
                        mrole = guild.get_role(mute_role_id)
                        if mrole is None:
                            try:
                                mrole = await guild.fetch_role(mute_role_id)
                            except discord.NotFound:
                                mrole = None
                            except discord.HTTPException as e:
                                logger.exception(
                                    "[event] user_unmute - %s: Failed to fetch mute role %s in guild %s: %s",  # noqa: E501
                                    data.category,
                                    mute_role_id,
                                    data.guild_id,
                                    e,
                                )
                                mrole = None
                    if not mute_role_id or mrole is None:
                        logger.error(
                            "[event] user_unmute - %s: Mute role %s not found in guild %s",  # noqa: E501
                            data.category,
                            mute_role_id,
                            data.guild_id,
                        )
                    else:
                        member_roles = {r.id for r in member.roles}
                        has_role = mute_role_id in member_roles
                        if not has_role:
                            logger.error(
                                "[event] user_unmute - %s: User %s does not have mute role %s",  # noqa: E501
                                data.category,
                                member.id,
                                mute_role_id,
                            )
                        else:
                            try:
                                await member.remove_roles(mrole)
                            except Exception as e:
                                logger.exception(
                                    "[event] user_unmute - %s: Failed to remove mute role %s from user %s: %s",  # noqa: E501
                                    data.category,
                                    mute_role_id,
                                    member.id,
                                    e,
                                )
                                raise e
                case _:
                    ...

        gather_list: list[Awaitable[None]] = []

        # sending log message
        if logging_channel_id:
            gather_list.append(
                send_moderation_log(
                    self.bot, channel_id=logging_channel_id, event_data=data
                )
            )

        gather_list.append(
            send_unpunish_dm_message(
                self.bot,
                user=member,
                category=data.category,
                guild_name=guild.name,
            )
        )

        try:
            await asyncio.gather(*gather_list, return_exceptions=True)
        except Exception as e:
            logger.exception(
                "[event] on_user_muted - %s: Failed to send DM or log message: %s",  # noqa: E501
                data.category,
                e,
            )


async def setup(bot: Nightcore):
    """Setup the UserMutedEvent cog."""
    await bot.add_cog(UserMutedEvent(bot))
