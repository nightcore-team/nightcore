"""Count voice activity event."""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from discord import Member, VoiceState
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.operations import get_or_create_user

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


class CountVoiceActivityEvent(Cog):
    def __init__(self, bot: "Nightcore"):
        self.bot = bot

    @Cog.listener()
    async def on_count_voice_activity(
        self, member: Member, before: VoiceState, after: VoiceState
    ):
        """Count voice activity for users."""

        guild = member.guild

        async with self.bot.uow.start() as session:
            user, _ = await get_or_create_user(
                session,
                guild_id=guild.id,
                user_id=member.id,
            )

            now = datetime.now(timezone.utc)
            # join
            if before.channel is None and after.channel is not None:
                # start counting
                try:
                    user.temp_voice_activity = now
                except Exception as e:
                    logger.exception(
                        "[voice/count] Error starting voice activity count for user %s in guild %s: %s",  # noqa: E501
                        member.id,
                        guild.id,
                        e,
                    )
                    return

                logger.info(
                    "[voice/count] Start counting user voice %s activity in guild %s in %s",  # noqa: E501
                    member.id,
                    guild.id,
                    after.channel.id,
                )

            # leave
            elif before.channel is not None and after.channel is None:
                # stop counting
                if user.temp_voice_activity is None:
                    return

                total_seconds = (
                    now - user.temp_voice_activity
                ).total_seconds()
                try:
                    user.voice_activity += int(total_seconds)
                    user.temp_voice_activity = None
                    user.battle_pass_points += (
                        int(total_seconds) // 60
                    ) * 8  # 8 points per minute
                except Exception as e:
                    logger.exception(
                        "[voice/count] Error stopping voice activity count for user %s in guild %s: %s",  # noqa: E501
                        member.id,
                        guild.id,
                        e,
                    )
                    return

                logger.info(
                    "[voice/count] Stop counting user voice %s activity in guild %s in %s",  # noqa: E501
                    member.id,
                    guild.id,
                    before.channel.id,
                )

            # switch
            elif (
                before.channel is not None
                and after.channel is not None
                and before.channel.id != after.channel.id
            ):
                if after.channel == guild.afk_channel:
                    # stop counting
                    if user.temp_voice_activity is None:
                        return

                    total_seconds = (
                        now - user.temp_voice_activity
                    ).total_seconds()

                    try:
                        user.voice_activity += int(total_seconds)
                        user.temp_voice_activity = None
                        user.battle_pass_points += (
                            int(total_seconds) // 60
                        ) * 8  # 8 points per minute
                    except Exception as e:
                        logger.exception(
                            "[voice/count] Error stopping voice activity count for user %s in guild %s: %s",  # noqa: E501
                            member.id,
                            guild.id,
                            e,
                        )
                        return

                    logger.info(
                        "[voice/count] Stop counting user voice %s activity in guild %s in %s",  # noqa: E501
                        member.id,
                        guild.id,
                        before.channel.id,
                    )

                else:
                    # continue counting
                    return


async def setup(bot: "Nightcore"):
    """Setup the CountVoiceActivityEvent cog."""
    await bot.add_cog(CountVoiceActivityEvent(bot))
