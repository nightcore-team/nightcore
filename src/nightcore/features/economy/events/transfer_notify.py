"""Handle user items changed events in the economy feature."""

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.operations import create_transfer_money_record
from src.nightcore.features.economy.components.v2 import (
    TransferCoinsViewV2,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore
    from src.nightcore.features.economy.events.dto import (
        TransferCoinsEventDTO,
    )

from src.nightcore.utils.log import send_log_message

logger = logging.getLogger(__name__)


class TransferCoinsEvent(Cog):
    def __init__(self, bot: "Nightcore"):
        self.bot = bot

    async def _create_transfer_record(
        self,
        dto: "TransferCoinsEventDTO",
    ):
        """Create a transfer money record in the database."""
        async with self.bot.uow.start() as session:
            await create_transfer_money_record(
                session,
                guild_id=dto.guild.id,
                sender_id=dto.sender_id,
                receiver_id=dto.receiver.id,
                amount=dto.amount,
            )

    @Cog.listener()
    async def on_transfer_coins(
        self,
        dto: "TransferCoinsEventDTO",
    ):
        """Handle user items changed event."""

        try:
            await self._create_transfer_record(dto)
        except Exception as e:
            logger.exception(
                "[%s/log] Failed to create transfer record (reciever=%s sender=%s amount=%s) in guild %s: %s",  # noqa: E501
                dto.event_type,
                dto.receiver.id,
                dto.sender_id,
                dto.amount,
                dto.guild.id,
                e,
            )

        view = TransferCoinsViewV2(
            self.bot,
            user_id=dto.sender_id,
            item_name=dto.item_name,
            amount=dto.amount,
            comment=dto.comment,
        )

        if dto.logging_channel_id:
            try:
                await send_log_message(self.bot, dto)
            except Exception as e:
                logger.warning(
                    "[%s/log] Failed to send log message for guild %s: %s. log embed: %s",  # noqa: E501
                    dto.event_type,
                    dto.guild.id,
                    e,
                    dto.build_log_embed(self.bot).to_dict(),
                )
        else:
            logger.info(
                "[%s/log] No logging channel ID provided for guild %s",
                dto.event_type,
                dto.guild.id,
            )

        try:
            await dto.receiver.send(view=view)
        except discord.Forbidden:
            logger.info(
                "[%s/log] Failed to send DM to user %s because he doesn't accept DM",  # noqa: E501
                dto.event_type,
                dto.receiver.id,
            )
        except Exception as e:
            logger.warning(
                "[%s/log] Failed to send DM to user %s: %e",
                dto.event_type,
                dto.receiver.id,
                e,
            )

        logger.info(
            "[%s/log] - invoked sender=%s receiver=%s guild=%s item_name=%s amount=%s",  # noqa: E501
            dto.event_type,
            dto.sender_id,
            dto.receiver.id,
            dto.guild.id,
            dto.item_name,
            dto.amount,
        )


async def setup(bot: "Nightcore") -> None:
    """Setup the TransferCoinsEvent cog."""
    await bot.add_cog(TransferCoinsEvent(bot))
