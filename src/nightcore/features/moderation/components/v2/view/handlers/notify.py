"""Handler for notify revoke button."""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from discord import Guild, Message
from discord.components import TextDisplay as TextDisplayOverride
from discord.interactions import Interaction

from src.infra.db.operations import get_user_notify_by_end_time
from src.nightcore.features.tickets.utils import extract_str_by_pattern
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.utils._enums import NotifyStateEnum

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


@check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)
async def handle_notify_revoke_button(
    interaction: Interaction["Nightcore"],
) -> None:
    """Handle notify revoke button callback."""
    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    message = cast(Message, interaction.message)

    end_time = None

    for component in message.components:
        for item in component.children:  # type: ignore
            if isinstance(item, TextDisplayOverride):
                match item.id:
                    case 8:
                        end_time = datetime.fromtimestamp(
                            float(
                                extract_str_by_pattern(
                                    item.content, r"<t:(\d+):[A-Za-z]>"
                                )  # type: ignore
                            ),
                            tz=UTC,
                        )
                    case _:
                        ...

    async with bot.uow.start() as session:
        notifystate = await get_user_notify_by_end_time(
            session,
            guild_id=guild.id,
            message_id=message.id,
            ts=cast(int, cast(datetime, end_time).timestamp()),
        )
        if not notifystate or notifystate.state != NotifyStateEnum.PENDING:
            logger.error(
                "[notify] No pending notify state found "
                "in guild %s, message %s",
                guild.id,
                message.id,
            )
        else:
            await session.delete(notifystate)

    await message.delete()
