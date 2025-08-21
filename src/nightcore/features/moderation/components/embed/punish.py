"""Embed components for punishment notifications."""

import datetime

from discord import Embed

"""
from *.utils import types
"""


def generate_dm_punish_embed(
    punish_type: str,
    guild_name: str,
    moderator: str,
    reason: str,
    end_time: datetime.datetime | None,
    bot_name: str,
) -> Embed:
    embed = Embed(
        title=f"{punish_type.capitalize()} Notification",
        description=f"You have been {punish_type} from **{guild_name}**",
        color=0xFF0000,
    )
    embed.add_field(name="Moderator", value=moderator, inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    if end_time:
        embed.add_field(name="End Time", value=end_time, inline=False)
    embed.set_footer(text=f"Powered by {bot_name}")
    return embed
