"""Utilities for generating and formatting channel permission overwrites."""

import io

import discord

PERMISSION_NAME_MAP = [
    ("create_instant_invite", "Create Invites"),
    ("kick_members", "Kick Members"),
    ("ban_members", "Ban Members"),
    ("administrator", "Administrator"),
    ("manage_channels", "Manage Channels"),
    ("manage_guild", "Manage Server"),
    ("add_reactions", "Add Reactions"),
    ("view_audit_log", "View Audit Log"),
    ("view_channel", "View Channel"),
    ("send_messages", "Send Messages"),
    ("send_tts_messages", "Send TTS Messages"),
    ("manage_messages", "Manage Messages"),
    ("embed_links", "Embed Links"),
    ("attach_files", "Attach Files"),
    ("read_message_history", "Read Message History"),
    ("mention_everyone", "Mention Everyone"),
    ("use_external_emojis", "Use External Emojis"),
    ("view_guild_insights", "View Server Insights"),
    ("connect", "Connect (Voice)"),
    ("speak", "Speak (Voice)"),
    ("mute_members", "Mute Members"),
    ("deafen_members", "Deafen Members"),
    ("move_members", "Move Members"),
    ("use_voice_activation", "Use Voice Activity"),
    ("change_nickname", "Change Nickname"),
    ("manage_nicknames", "Manage Nicknames"),
    ("manage_roles", "Manage Roles"),
    ("manage_webhooks", "Manage Webhooks"),
    ("manage_expressions", "Manage Expressions"),
    ("use_application_commands", "Use Application Commands"),
    ("request_to_speak", "Request to Speak"),
    ("manage_events", "Manage Events"),
    ("manage_threads", "Manage Threads"),
    ("create_public_threads", "Create Public Threads"),
    ("create_private_threads", "Create Private Threads"),
    ("use_external_stickers", "Use External Stickers"),
    ("send_messages_in_threads", "Send Messages in Threads"),
    ("use_embedded_activities", "Use Embedded Activities"),
    ("moderate_members", "Moderate Members"),
    ("use_soundboard", "Use Soundboard"),
    ("create_expressions", "Create Expressions"),
    ("create_events", "Create Events"),
    ("use_external_sounds", "Use External Sounds"),
    ("send_voice_messages", "Send Voice Messages"),
    ("send_polls", "Send Polls"),
    ("use_external_apps", "Use External Apps"),
    ("stream", "Stream Video"),
    ("priority_speaker", "Priority Speaker"),
]


def _state_symbol(value: bool | None) -> str:
    if value is True:
        return "✔"
    if value is False:
        return "✖"
    return "/"


def build_channel_overwrites_text(channel: discord.abc.GuildChannel) -> str:
    """Returns a human-readable text representation of the channel's permission overwrites."""  # noqa: E501
    if not hasattr(channel, "overwrites"):
        return "This channel type does not support permission overwrites."

    lines: list[str] = []

    # channel.overwrites returns mapping: target (Role/User) -> PermissionOverwrite  # noqa: E501
    overwrites = channel.overwrites

    if not overwrites:
        return "There are no permission overwrites for this channel."

    for target, overwrite in overwrites.items():
        if isinstance(target, discord.Role):
            if target.is_default():
                header = f"Role @everyone ({target.id}):"
            else:
                header = f"Role {target.name} ({target.id}):"
        elif isinstance(target, discord.Member | discord.User):
            header = f"User {target.display_name} ({target.id}):"
        else:
            header = f"Object {getattr(target, 'id', 'N/A')}:"

        lines.append(header)

        for attr, human_name in PERMISSION_NAME_MAP:
            value = getattr(overwrite, attr, None)
            lines.append(f" {human_name}: {_state_symbol(value)}")

        lines.append("")  # Blank line between targets

    return "\n".join(lines).rstrip() + "\n"


def build_channel_overwrites_file(
    channel: discord.abc.GuildChannel,
) -> discord.File:
    """Generate a discord.File containing the channel's permission overwrites."""  # noqa: E501
    text = build_channel_overwrites_text(channel)
    buffer = io.BytesIO(text.encode("utf-8"))
    safe_channel_name = getattr(channel, "name", f"channel_{channel.id}")
    filename = f"permissions_{safe_channel_name}_{channel.id}.txt"
    return discord.File(
        buffer,
        filename=filename,
        description="List of channel permission overwrites",
    )
