"""Roles Changes Event Cog for Nightcore Bot."""

import logging
from datetime import UTC
from typing import TYPE_CHECKING

import discord
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildLoggingConfig, MainGuildConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import (
    create_punish,
    get_specified_channel,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore
    from src.nightcore.features.moderation.events import RolesChangeEventData

from src.nightcore.features.moderation.utils.punish_notify import (
    send_moderation_log,
    send_rr_channel_log,
)

logger = logging.getLogger(__name__)


class RolesChangeEvent(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @Cog.listener()
    async def on_roles_change(
        self,
        *,
        data: "RolesChangeEventData",
        _send_to_rr_channel: bool = False,
        _create_punish: bool = True,
    ) -> None:
        """Handle roles changes events."""

        logger.info(
            "[event] on_roles_change - %s: Guild: %s, Member: %s, Role(-s): %s, Option: %s",  # noqa: E501
            data.category,
            data.moderator.guild.id,
            data.user.id,
            ", ".join(f"<@&{role}>" for role in data.roles_ids),
            data.option,
        )

        rr_channel_id: int | None = None

        try:
            async with self.bot.uow.start() as session:
                if _create_punish:
                    await create_punish(
                        session,
                        guild_id=data.moderator.guild.id,
                        user_id=data.user.id,
                        moderator_id=data.moderator.id,
                        category=data.category,
                        reason=data.reason,
                        time_now=discord.utils.utcnow().astimezone(UTC),
                    )

                if _send_to_rr_channel:
                    rr_channel_id = await get_specified_channel(
                        session,
                        guild_id=data.moderator.guild.id,
                        config_type=MainGuildConfig,
                        channel_type=ChannelType.ROLE_REQUESTS,
                    )

                logging_channel_id = await get_specified_channel(
                    session,
                    guild_id=data.moderator.guild.id,
                    config_type=GuildLoggingConfig,
                    channel_type=ChannelType.LOGGING_MODERATION,
                )
        except Exception as e:
            logger.exception(
                "[event] on_roles_change - %s: Failed to create punish record: %s",  # noqa: E501
                data.category,
                e,
            )
            return

        if logging_channel_id:
            try:
                await send_moderation_log(
                    self.bot,
                    channel_id=logging_channel_id,
                    event_data=data,
                )
            except Exception as e:
                logger.warning(
                    "[event] on_roles_change - %s: Guild: %s, failed to send log message: %s, log embed: %s",  # noqa: E501
                    data.category,
                    data.moderator.guild.id,
                    e,
                    data.build_embed(self.bot).to_dict(),
                )

        else:
            logger.info(
                "[event] on_roles_change - %s: Guild: %s, logging channel is not set",  # noqa: E501
                data.category,
                data.moderator.guild.id,
            )

        if rr_channel_id:
            try:
                await send_rr_channel_log(
                    self.bot, channel_id=rr_channel_id, event_data=data
                )
            except Exception as e:
                logger.warning(
                    "[event] on_roles_change - %s: Guild: %s, failed to send log message(rr channel): %s, log embed: %s",  # noqa: E501
                    data.category,
                    data.moderator.guild.id,
                    e,
                    data.build_embed(self.bot).to_dict(),
                )
        else:
            logger.info(
                "[event] on_roles_change - %s: Guild: %s, role request channel is not set",  # noqa: E501
                data.category,
                data.moderator.guild.id,
            )


async def setup(bot: "Nightcore"):
    """Setup the RolesChangeEvent cog."""
    await bot.add_cog(RolesChangeEvent(bot))
