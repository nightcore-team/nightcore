"""Embed components for punishment notifications."""

from datetime import datetime, timezone

from discord import Embed, Member

from src.nightcore.bot import Nightcore

"""
from *.utils import types
"""


def generate_log_punish_embed(
    bot: Nightcore,
    punish_type: str,
    moderator_id: int,
    user_id: int,
    reason: str,
    duration: str | None = None,
    end_time: datetime | None = None,
):
    """Generate an embed for punishment log notification."""
    embed = Embed(title=f"[{punish_type}] {user_id}", color=0xFF0000)
    embed.add_field(name="Moderator", value=f"<@{moderator_id}>", inline=True)
    embed.add_field(name="User", value=f"<@{user_id}>", inline=True)
    embed.add_field(name="Reason", value=reason, inline=True)

    if duration:
        embed.add_field(name="Duration", value=duration, inline=True)

    if end_time:
        embed.add_field(name="End Time", value=end_time, inline=True)

    embed.set_footer(
        text=f"Powered by {bot.user.name}",  # type: ignore
        icon_url=bot.user.avatar.url,  # type: ignore
    )
    embed.timestamp = datetime.now(timezone.utc)

    return embed


def generate_dm_punish_embed(
    punish_type: str,
    guild_name: str,
    moderator: Member,
    reason: str,
    end_time: datetime | None,
    bot: Nightcore,
) -> Embed:
    """Generate an embed for DM punishment notification."""
    embed = Embed(
        title=f"{punish_type.capitalize()} Notification",
        description=f"You have been {punish_type} from **{guild_name}**",
        color=0xFF0000,
    )
    embed.add_field(
        name="Moderator",
        value=f"{moderator.name} | {moderator.id}",
        inline=False,
    )
    embed.add_field(name="Reason", value=reason, inline=False)

    if end_time:
        embed.add_field(name="End Time", value=end_time, inline=False)

    embed.set_footer(
        text=f"Powered by {bot.user.name}",  # type: ignore
        icon_url=bot.user.avatar.url,  # type: ignore
    )

    return embed
