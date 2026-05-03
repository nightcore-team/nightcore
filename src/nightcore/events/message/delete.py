"""Message events module."""

import asyncio
import io
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from discord import Color, Embed, File, Message
from discord.ext.commands import Cog  # type: ignore
from discord.raw_models import RawBulkMessageDeleteEvent, RawMessageDeleteEvent

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import get_specified_channel, get_specified_field

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import ensure_messageable_channel_exists

logger = logging.getLogger(__name__)


class DeleteMessageEvent(Cog):
    def __init__(self, bot: "Nightcore"):
        self.bot = bot

    async def _get_logging_and_ignoring_channels_ids(
        self, guild_id: int
    ) -> tuple[int | None, list[int] | None]:
        async with self.bot.uow.start() as session:
            logging_channel_id = await get_specified_channel(
                session,
                guild_id=guild_id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_MESSAGES,
            )

            ignoring_channels_ids = cast(
                list[int] | None,
                await get_specified_field(
                    session,
                    guild_id=guild_id,
                    config_type=GuildLoggingConfig,
                    field_name="message_log_ignoring_channels_ids",
                ),
            )

        return logging_channel_id, ignoring_channels_ids

    def _build_message_embed(
        self, message: Message, event_type: str | None = None
    ) -> tuple[Embed, list[File]]:
        embed = Embed(
            color=Color.red(),
            timestamp=datetime.now(UTC),
        )
        embed.set_author(name="Сообщение было удалено")

        embed.set_footer(
            text="Powered by nightcore",
            icon_url=self.bot.user.display_avatar.url,
        )

        files: list[File] = []

        # message content
        content = message.content or ""
        if content:
            if len(content) > 1024:
                files.append(
                    File(
                        io.BytesIO(content.encode("utf-8")),
                        filename=f"{message.id}.txt",
                    )
                )
            else:
                embed.add_field(
                    name="Удаленное сообщение:", value=content, inline=False
                )

        embed.add_field(name="ID сообщения:", value=message.id, inline=False)

        attachments_text = ""
        if message.attachments:
            for attachment in message.attachments:
                url = attachment.url
                proxy_url = getattr(attachment, "proxy_url", None) or url
                attachments_text += (
                    f"[URL](<{url}>) | [PROXY_URL](<{proxy_url}>)\n"
                )

            if len(attachments_text) > 1024:
                files.append(
                    File(
                        io.BytesIO(attachments_text.encode("utf-8")),
                        filename=f"{message.id}_attachments.txt",
                    )
                )
            elif attachments_text:
                embed.add_field(
                    name="Вложения:", value=attachments_text, inline=False
                )

        if event_type == "bulk":
            embed.add_field(name="Причина", value="/clear")

        embed.add_field(name="Автор:", value=message.author.mention)
        embed.add_field(name="Канал:", value=f"<#{message.channel.id}>")

        return embed, files

    @Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent):
        """Handle message delete events."""

        message = payload.cached_message
        if not message:
            logger.info(
                "[message] Deleted message not found in cache: %s", payload
            )
            return

        guild = message.guild
        if not guild:
            logger.info(
                "[message] Deleted message is not from a guild: %s", payload
            )
            return

        (
            logging_channel_id,
            ignoring_channels_ids,
        ) = await self._get_logging_and_ignoring_channels_ids(guild.id)

        if logging_channel_id is None:
            logger.info(
                "[message] Logging channel not configured for guild %s",
                guild.id,
            )
            return

        if ignoring_channels_ids:
            if message.channel.id in ignoring_channels_ids:
                logger.info(
                    "[message] Message can't be deleted from ignored channel %s in guild %s",  # noqa: E501
                    message.channel.id,
                    guild.id,
                )
                return
        else:
            logger.info(
                "[message] No ignoring channels configured for guild %s",
                guild.id,
            )

        channel = await ensure_messageable_channel_exists(
            guild=guild, channel_id=logging_channel_id
        )
        if not channel:
            logger.info(
                "[message] Logging channel %s not found in guild %s",
                logging_channel_id,
                guild.id,
            )
            return

        embed, files = self._build_message_embed(message)

        try:
            await channel.send(embed=embed, files=files)  # type: ignore
        except Exception as e:
            logger.error(
                "[message] Failed to send deleted message log to channel %s in guild %s: %s",  # noqa: E501
                channel.id,
                guild.id,
                e,
            )

        logger.info("[message] Message deleted: %s", message)

        return

    @Cog.listener()
    async def on_raw_bulk_message_delete(
        self, payload: RawBulkMessageDeleteEvent
    ):
        """Handle bulk message delete events."""

        messages = payload.cached_messages

        if not messages:
            logger.info(
                "[message] Deleted messages not found in cache: %s", payload
            )
            return

        guild = messages[0].guild
        if not guild:
            logger.info(
                "[message] Deleted message is not from a guild: %s", payload
            )
            return

        (
            logging_channel_id,
            ignoring_channels_ids,
        ) = await self._get_logging_and_ignoring_channels_ids(guild.id)

        if logging_channel_id is None:
            logger.info(
                "[message] Logging channel not configured for guild %s",
                guild.id,
            )
            return

        for message in messages:
            if (
                ignoring_channels_ids
                and message.channel.id in ignoring_channels_ids
            ):
                logger.info(
                    "[message] Message can't be deleted from ignored channel %s in guild %s",  # noqa: E501
                    message.channel.id,
                    guild.id,
                )
                continue

            embed, files = self._build_message_embed(
                message, event_type="bulk"
            )

            channel = await ensure_messageable_channel_exists(
                guild=guild, channel_id=logging_channel_id
            )
            if not channel:
                logger.info(
                    "[message] Logging channel %s not found in guild %s",
                    logging_channel_id,
                    guild.id,
                )
                return

            try:
                asyncio.create_task(channel.send(embed=embed, files=files))  # type: ignore
            except Exception as e:
                logger.error(
                    "[message] Failed to send deleted message log to channel %s in guild %s: %s",  # noqa: E501
                    channel.id,
                    guild.id,
                    e,
                )

            logger.info("[message] Message deleted: %s", message)


async def setup(bot: "Nightcore") -> None:
    """Setup the OnMessageEvent cog."""
    await bot.add_cog(DeleteMessageEvent(bot))
