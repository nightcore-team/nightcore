"""Embed components for punishment notifications."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from discord import Embed

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


def generate_log_punish_embed(
    bot: "Nightcore",
    punish_type: str,
    moderator_id: int,
    user_id: int,
    reason: str,
    duration: str | None = None,
    end_time: datetime | None = None,
    old_nickname: str | None = None,
    new_nickname: str | None = None,
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

    if old_nickname:
        embed.add_field(name="Old Nickname", value=old_nickname, inline=True)

    if new_nickname:
        embed.add_field(name="New Nickname", value=new_nickname, inline=True)

    embed.set_footer(
        text=f"Powered by {bot.user.name}",  # type: ignore
        icon_url=bot.user.avatar.url,  # type: ignore
    )
    embed.timestamp = datetime.now(UTC)

    return embed
