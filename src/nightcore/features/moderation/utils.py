"""Utility functions for moderation commands."""

import logging

from discord import Guild, Member, User

from src.nightcore.bot import Nightcore
from src.nightcore.features.moderation.components.embed.punish import (
    generate_dm_punish_embed,
)

logger = logging.getLogger(__name__)


def compare_top_roles(guild: Guild, member: Member) -> bool:
    """Compares the top roles of the bot and a member to determine if the bot can kick the member."""  # noqa: E501
    if guild.owner_id == member.id:
        return False

    if not guild.me.roles:
        return False

    if not member.roles:
        return True

    bot_top_role = guild.me.top_role.position
    member_top_role = member.top_role.position

    return bot_top_role > member_top_role


async def send_punish_dm_message(
    bot: Nightcore,
    moderator: Member,
    user: User,
    punish_type: str,
    reason: str,
) -> None:
    logger.info("member: %s, moderator: %s", user, moderator)
    embed = generate_dm_punish_embed(
        punish_type=punish_type,
        guild_name=moderator.guild.name,
        moderator=moderator.name,
        reason=reason,
        end_time=None,
        bot_name=bot.user.name,  # type: ignore
    )
    try:
        await user.send(embed=embed)
    except Exception as e:
        logger.exception("Failed to send DM to %s: %s", user, e)
