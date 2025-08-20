"""Utility functions for moderation commands."""

from discord import Guild, Member


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
