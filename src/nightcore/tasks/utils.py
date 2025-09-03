"""Utility functions for tasks."""

from datetime import datetime, timezone
from typing import cast

from discord import ClientUser

from src.infra.db.models import TempPunish
from src.nightcore.bot import Nightcore
from src.nightcore.features.moderation.events import UnPunishEventData


def handle_infraction_type_event(active_punish: TempPunish, bot: Nightcore):
    """Handle specific events based on infraction type."""
    if active_punish.category.lower() == "mute":
        data = UnPunishEventData(
            category=active_punish.category,
            guild_id=active_punish.guild_id,
            moderator_id=cast(ClientUser, bot.user).id,
            user_id=active_punish.user_id,
            reason="Punish expired",
            created_at=datetime.now(timezone.utc),
        )
        bot.dispatch("user_unmute", data=data)
