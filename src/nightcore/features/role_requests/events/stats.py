"""Stats provided by user event module."""

import logging

import discord
from discord.ext.commands import Cog  # type: ignore
from discord.ui import Button

from src.infra.db.models._enums import RoleRequestStateEnum
from src.infra.db.operations import get_latest_user_role_request
from src.nightcore.bot import Nightcore
from src.nightcore.features.role_requests.components.v2 import (
    CheckRoleRequestView,
    RoleRequestStateView,
)
from src.nightcore.utils import (
    ensure_member_exists,
    ensure_message_exists,
    ensure_messageable_channel_exists,
)

logger = logging.getLogger(__name__)


class StatsProvidedEvent(Cog):
    def __init__(self, bot: Nightcore):
        self.bot = bot

    @Cog.listener()
    async def on_stats_provided(self, message: discord.Message):
        """Handle stats provided event."""
        try:
            async with self.bot.uow.start() as session:
                if not (
                    last_rr := await get_latest_user_role_request(
                        session, guild_id=None, user_id=message.author.id
                    )
                ):
                    return
        except Exception as e:
            logger.error("Failed to fetch role request from db: %s", e)
            return

        if last_rr.state != RoleRequestStateEnum.REQUESTED:
            return

        if not (guild := self.bot.get_guild(last_rr.guild_id)):
            return

        if not (
            member := await ensure_member_exists(guild, last_rr.author_id)
        ):
            return

        if not (
            channel := await ensure_messageable_channel_exists(
                guild, last_rr.channel_id
            )
        ):
            return

        if not (
            rr_message := await ensure_message_exists(
                self.bot, channel, last_rr.message_id
            )
        ):
            return

        try:
            attachments = [
                discord.MediaGalleryItem(att.url)
                for att in message.attachments
            ]
            view = CheckRoleRequestView(
                self.bot,
                interaction_user_id=message.author.id,
                interaction_user_nick=member.display_name,
                role_requested_id=last_rr.role_id,
                moderator_id=last_rr.moderator_id,
                state=last_rr.state,
                attachments=attachments,
            )
            button = view.get_component("role_request:stats")
            if isinstance(button, Button):
                button.disabled = True

        except Exception as e:
            logger.error("Failed to create CheckRoleRequestView: %s", e)
            return

        try:
            updated_view = await rr_message.edit(view=view)
            await updated_view.reply(
                view=RoleRequestStateView(
                    self.bot,
                    moderator_id=last_rr.moderator_id,
                    user_id=last_rr.author_id,
                    state=RoleRequestStateEnum.STATS_PROVIDED,
                    message_url=rr_message.jump_url,
                    image_url=message.attachments[0].url
                    if message.attachments
                    else None,
                    image_proxy_url=message.attachments[0].proxy_url
                    if message.attachments
                    else None,
                )
            )
        except Exception as e:
            logger.error(
                "Failed to edit role request message for user %s in guild %s: %s",  # noqa: E501
                member.id,
                guild.id,
                e,
            )
            return

        try:
            await message.reply(
                "Ваша статистика была успешно отправлена модератору, ожидайте ответа.",  # noqa: E501
            )
        except Exception as e:
            logger.error(
                "Failed to reply to user %s in DM: %s",
                member.id,
                e,
            )
            return

        async with self.bot.uow.start() as session:
            if not (
                last_rr := await get_latest_user_role_request(
                    session, guild_id=None, user_id=message.author.id
                )
            ):
                return

            last_rr.state = RoleRequestStateEnum.STATS_PROVIDED

        logger.info("Message received: %s", message)
        return


async def setup(bot: Nightcore):
    """Setup the StatsProvidedEvent cog."""
    await bot.add_cog(StatsProvidedEvent(bot))
