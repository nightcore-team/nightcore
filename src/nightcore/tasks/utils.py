"""Utility functions for tasks."""

from datetime import datetime, timezone
from typing import cast

from discord import ClientUser

from src.infra.db.models import TempPunish
from src.nightcore.bot import Nightcore
from src.nightcore.features.moderation.events import (
    UnPunishEventData,
    UserUnmutedEventData,
)


def handle_infraction_type_event(active_punish: TempPunish, bot: Nightcore):
    """Handle specific events based on infraction type."""
    match active_punish.category.lower():
        case "mute":
            m = UserUnmutedEventData(
                mode="expired",
                category=active_punish.category,
                mute_type="default",
                guild_id=active_punish.guild_id,
                moderator_id=cast(ClientUser, bot.user).id,
                user_id=active_punish.user_id,
                reason="Punish expired",
                created_at=datetime.now(timezone.utc),
            )
            bot.dispatch("user_unmute", data=m)

        case "mpmute":
            mpm = UserUnmutedEventData(
                mode="expired",
                category=active_punish.category,
                mute_type="mpmute",
                guild_id=active_punish.guild_id,
                moderator_id=cast(ClientUser, bot.user).id,
                user_id=active_punish.user_id,
                reason="Punish expired",
                created_at=datetime.now(timezone.utc),
            )
            bot.dispatch("user_unmute", data=mpm)

        case "vmute":
            vm = UserUnmutedEventData(
                mode="expired",
                category=active_punish.category,
                mute_type="vmute",
                guild_id=active_punish.guild_id,
                moderator_id=cast(ClientUser, bot.user).id,
                user_id=active_punish.user_id,
                reason="Punish expired",
                created_at=datetime.now(timezone.utc),
            )
            bot.dispatch("user_unmute", data=vm)

        case "ticketban":
            t = UnPunishEventData(
                mode="expired",
                category=active_punish.category,
                guild_id=active_punish.guild_id,
                moderator_id=cast(ClientUser, bot.user).id,
                user_id=active_punish.user_id,
                reason="Punish expired",
                created_at=datetime.now(timezone.utc),
            )
            bot.dispatch("user_unticketbanned", data=t)

        case "ban":
            b = UnPunishEventData(
                mode="expired",
                category=active_punish.category,
                guild_id=active_punish.guild_id,
                moderator_id=cast(ClientUser, bot.user).id,
                user_id=active_punish.user_id,
                reason="Punish expired",
                created_at=datetime.now(timezone.utc),
            )
            bot.dispatch("user_unbanned", data=b)

        case "rrban":
            rr = UnPunishEventData(
                mode="expired",
                category=active_punish.category,
                guild_id=active_punish.guild_id,
                moderator_id=cast(ClientUser, bot.user).id,
                user_id=active_punish.user_id,
                reason="Punish expired",
                created_at=datetime.now(timezone.utc),
            )
            bot.dispatch("user_unrole_request_banned", data=rr)

        case _:
            ...
