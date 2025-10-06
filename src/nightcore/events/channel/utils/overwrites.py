"""Utilities for generating and formatting channel permission overwrites and changes."""  # noqa: E501

import io

import discord

from ._types import PERMISSION_NAME_MAP  # type: ignore


def _state_symbol(value: bool | None) -> str:
    """Return a symbol representing an overwrite state (allow, deny, unset)."""
    if value is True:
        return "✔"  # Explicitly allowed
    if value is False:
        return "✖"  # Explicitly denied
    return "/"  # Not set / inherited


def _build_channel_overwrites_text(channel: discord.abc.GuildChannel) -> str:
    """Return a human-readable text representation of the channel's permission overwrites."""  # noqa: E501
    if not hasattr(channel, "overwrites"):
        return "This channel type does not support permission overwrites."

    overwrites = channel.overwrites
    if not overwrites:
        return "There are no permission overwrites for this channel."

    lines: list[str] = []

    for target, overwrite in overwrites.items():
        # Identify target type (role, default role, user, or unknown object)
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

        # List each permission state
        for attr, human_name in PERMISSION_NAME_MAP:
            value = getattr(overwrite, attr, None)
            lines.append(f" {human_name}: {_state_symbol(value)}")

        lines.append("")  # Blank line between targets

    # Ensure newline at end for consistent file output
    return "\n".join(lines).rstrip() + "\n"


def build_channel_overwrites_file(
    channel: discord.abc.GuildChannel,
) -> discord.File:
    """Generate a discord.File containing the channel's permission overwrites."""  # noqa: E501
    text = _build_channel_overwrites_text(channel)
    buffer = io.BytesIO(text.encode("utf-8"))  # In-memory text buffer
    safe_channel_name = getattr(channel, "name", f"channel_{channel.id}")
    filename = f"permissions_{safe_channel_name}_{channel.id}.txt"
    return discord.File(
        buffer,
        filename=filename,
        description="List of channel permission overwrites",
    )


def _safe_mention(
    target_id: int,
    guild: discord.Guild,
) -> str:
    """Return a safe mention for a permission overwrite target (role/member or raw ID)."""  # noqa: E501
    role = guild.get_role(target_id)
    if role:
        return f"<@&{role.id}>"
    member = guild.get_member(target_id)
    if member:
        return f"<@{member.id}>"
    return f"`{target_id}`"  # Fallback to code-formatted ID


class PermissionChange:
    """Container representing a before/after overwrite difference."""

    def __init__(
        self,
        old: discord.PermissionOverwrite,
        new: discord.PermissionOverwrite,
    ):
        self.old = old
        self.new = new


def _extract_overwrites_map(
    channel: discord.abc.GuildChannel,
) -> dict[int, discord.PermissionOverwrite]:
    """Return a mapping of target_id -> PermissionOverwrite for a channel."""
    result: dict[int, discord.PermissionOverwrite] = {}
    for target, overwrite in getattr(channel, "overwrites", {}).items():
        result[target.id] = overwrite
    return result


def _diff_permission_overwrites(
    old_channel: discord.abc.GuildChannel,
    new_channel: discord.abc.GuildChannel,
) -> tuple[
    list[tuple[int, discord.PermissionOverwrite]],
    list[tuple[int, discord.PermissionOverwrite]],
    dict[int, PermissionChange],
]:
    """
    Compute added, removed, and changed permission overwrites between two channel states.

    Returns:
        added:   list of (target_id, overwrite) newly present in new_channel
        removed: list of (target_id, overwrite) present before but not now
        changed: mapping target_id -> PermissionChange for modified overwrites
    """  # noqa: E501
    added: list[tuple[int, discord.PermissionOverwrite]] = []
    removed: list[tuple[int, discord.PermissionOverwrite]] = []
    changed: dict[int, PermissionChange] = {}

    old_map = _extract_overwrites_map(old_channel)
    new_map = _extract_overwrites_map(new_channel)

    # Determine removed overwrites
    for oid, ooverwrite in old_map.items():
        if oid not in new_map:
            removed.append((oid, ooverwrite))

    # Determine added and changed overwrites
    for nid, noverwrite in new_map.items():
        if nid not in old_map:
            added.append((nid, noverwrite))
        else:
            o = old_map[nid]
            if _overwrite_changed(o, noverwrite):
                changed[nid] = PermissionChange(o, noverwrite)

    return added, removed, changed


def _overwrite_changed(
    old: discord.PermissionOverwrite, new: discord.PermissionOverwrite
) -> bool:
    """Return True if any tracked permission attribute differs between two overwrites."""  # noqa: E501
    for attr, _ in PERMISSION_NAME_MAP:
        if getattr(old, attr, None) != getattr(new, attr, None):
            return True
    return False


def _format_added_removed_permission_block(
    items: list[tuple[int, discord.PermissionOverwrite]], guild: discord.Guild
) -> list[str]:
    """Format added or removed overwrite blocks into bullet list sections."""
    blocks: list[str] = []
    for target_id, overwrite in items:
        perms_lines: list[str] = []
        # Only include permissions explicitly set (omit inherited)
        for attr, human in PERMISSION_NAME_MAP:
            val = getattr(overwrite, attr, None)
            symbol = _state_symbol(val)
            if symbol != "/":
                perms_lines.append(f"{human}: {symbol}")
        if perms_lines:
            mention = _safe_mention(target_id, guild)
            blocks.append(f"* {mention}:\n  " + "\n  ".join(perms_lines))
    return blocks


def _format_changed_permission_block(
    changed: dict[int, PermissionChange], guild: discord.Guild
) -> list[str]:
    """Format changed overwrite entries showing before → after transitions."""
    blocks: list[str] = []
    for target_id, change in changed.items():
        perms_lines: list[str] = []
        for attr, human in PERMISSION_NAME_MAP:
            old_state = _state_symbol(getattr(change.old, attr, None))
            new_state = _state_symbol(getattr(change.new, attr, None))
            if old_state != new_state:
                perms_lines.append(f"{human}: {old_state} → {new_state}")
        if perms_lines:
            mention = _safe_mention(target_id, guild)
            blocks.append(f"* {mention}:\n  " + "\n  ".join(perms_lines))
    return blocks


def build_permission_changes_field(
    old_channel: discord.abc.GuildChannel,
    new_channel: discord.abc.GuildChannel,
    guild: discord.Guild,
) -> str | None:
    """
    Build a formatted multiline string summarizing permission overwrite changes
    between two channel states, or None if there are no differences.
    """  # noqa: D205
    added, removed, changed = _diff_permission_overwrites(
        old_channel, new_channel
    )

    sections: list[str] = []

    if added:
        blocks = _format_added_removed_permission_block(added, guild)
        if blocks:
            sections.append("\n".join(blocks))
    if removed:
        blocks = _format_added_removed_permission_block(removed, guild)
        if blocks:
            sections.append("\n".join(blocks))
    if changed:
        blocks = _format_changed_permission_block(changed, guild)
        if blocks:
            sections.append("\n".join(blocks))

    if sections:
        return "\n\n".join(sections)
    return None
