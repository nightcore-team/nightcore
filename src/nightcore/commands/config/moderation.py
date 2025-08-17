"""Moderation configuration commands for the Nightcore bot."""

import logging
from typing import Literal, cast

import discord
from discord import Guild, app_commands
from discord.embeds import Embed
from discord.interactions import Interaction, InteractionCallbackResponse

from src.nightcore.bot import Nightcore
from src.nightcore.commands.config._groups import (
    moderation as moderation_group,
)
from src.nightcore.components.embed.error import NoOptionsSuppliedEmbed
from src.nightcore.services.config import open_guild_config
from src.nightcore.utils.config_commands import (
    FieldSpec,
    apply_field_changes,
    format_changes,
    int_id_value,
    list_csv,
    split_changes,
    str_value,
    update_id_list,
)

logger = logging.getLogger(__name__)


@moderation_group.command(
    name="setup", description="Configure moderation settings."
)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    moderation_access_roles="The roles that can access moderation features.",
    ban_access_roles="The roles that can access ban features.",
    ban_request_ping_role="The role to ping when a ban request is made.",
    ban_request_channel="The channel where ban requests are made.",
    new_tickets_category="The category for new tickets.",
    pinned_tickets_category="The category for pinned tickets.",
    closed_tickets_category="The category for closed tickets.",
    ticket_created_ping_role="The role to ping when a ticket is created.",
    notifications_channel="The channel for notifications.",
    moderation_notifications_channel="The channel for notifications related to moderation.",  # noqa: E501
    mute_type="The type of mute to apply. Timeout | Role",
    mute_role="The role to assign when a user is muted.",
    mpmute_role="The role to assign when a user is muted in a specific channel.",  # noqa: E501
    vmute_role="The role to assign when a user is voice muted.",
    leaders_access_rr_roles="The roles that can access the leader's report.",
)
@app_commands.choices(
    mute_type=[
        app_commands.Choice(name="Timeout", value="timeout"),
        app_commands.Choice(name="Role", value="role"),
    ]
)
async def setup_moderation(
    interaction: Interaction,
    moderation_access_roles: str | None = None,
    ban_access_roles: str | None = None,
    ban_request_ping_role: discord.Role | None = None,
    ban_request_channel: discord.TextChannel | None = None,
    new_tickets_category: discord.CategoryChannel | None = None,
    pinned_tickets_category: discord.CategoryChannel | None = None,
    closed_tickets_category: discord.CategoryChannel | None = None,
    ticket_created_ping_role: discord.Role | None = None,
    notifications_channel: discord.TextChannel | None = None,
    moderation_notifications_channel: discord.TextChannel | None = None,
    mute_type: Literal["timeout", "role"] | None = None,
    mute_role: discord.Role | None = None,
    mpmute_role: discord.Role | None = None,
    vmute_role: discord.Role | None = None,
    leaders_access_rr_roles: str | None = None,
):
    """Configure moderation settings."""

    specs: list[FieldSpec | None] = [
        int_id_value("ban_request_ping_role_id", ban_request_ping_role),
        int_id_value("send_ban_request_channel_id", ban_request_channel),
        int_id_value("new_tickets_category_id", new_tickets_category),
        int_id_value("pinned_tickets_category_id", pinned_tickets_category),
        int_id_value("closed_tickets_category_id", closed_tickets_category),
        int_id_value("create_ticket_channel_id", ticket_created_ping_role),
        int_id_value("notifications_channel_id", notifications_channel),
        int_id_value(
            "notifications_for_moderation_channel_id",
            moderation_notifications_channel,
        ),
        int_id_value("mute_role_id", mute_role),
        int_id_value("mpmute_role_id", mpmute_role),
        int_id_value("vmute_role_id", vmute_role),
        list_csv("moderation_access_roles_ids", moderation_access_roles),
        list_csv("ban_access_roles_ids", ban_access_roles),
        list_csv("leaders_access_rr_roles_ids", leaders_access_rr_roles),
        str_value("mute_type", mute_type),
    ]

    specs = [s for s in specs if s is not None]

    if not specs:
        logger.info(
            "config.moderation.setup invoked user=%s guild=%s no_options_supplied",  # noqa: E501
            interaction.user.id,
            interaction.guild.id,  # type: ignore
        )
        return await interaction.response.send_message(
            embed=NoOptionsSuppliedEmbed(),
            ephemeral=True,
        )

    async with open_guild_config(
        cast(Nightcore, interaction.client),
        cast(Guild, interaction.guild).id,
    ) as guild_config:
        changes = apply_field_changes(guild_config, specs)  # type: ignore

    changed, skipped = split_changes(changes)
    description = format_changes(changed, skipped)

    logger.info(
        "config.moderation.setup invoked user=%s guild=%s updated=%s skipped=%s",  # noqa: E501
        interaction.user.id,
        cast(Guild, interaction.guild).id,
        changed,
        skipped,
    )
    return await interaction.response.send_message(
        embed=Embed(
            title="Moderation Configuration",
            description=description,
            color=discord.Color.green(),
        ),
        ephemeral=True,
    )


@moderation_group.command(name="update_moderation_access")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.choices(
    option=[
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Remove", value="remove"),
    ]
)
@app_commands.describe(
    role="The role to update",
    option="Whether to add or remove the role from the moderation access list",
)
async def update_moderation_access(
    interaction: Interaction,
    role: discord.Role,
    option: Literal["add", "remove"],
) -> InteractionCallbackResponse:
    """Update the list of roles with moderation access."""

    async with open_guild_config(
        cast(Nightcore, interaction.client),
        cast(Guild, interaction.guild).id,
    ) as guild_config:
        new_list, changed, state = update_id_list(
            guild_config.moderation_access_roles_ids,
            role.id,
            option,
        )
        if changed:
            guild_config.moderation_access_roles_ids = new_list

    if state == "exists":
        desc = f"Role <@&{role.id}> already in the moderation access list."
        color = discord.Color.yellow()
    elif state == "absent":
        desc = f"Role <@&{role.id}> not in the moderation access list."
        color = discord.Color.red()
    elif state == "added":
        desc = f"Role <@&{role.id}> added to the moderation access list."
        color = discord.Color.blurple()
    else:  # removed
        desc = f"Role <@&{role.id}> removed from the moderation access list."
        color = discord.Color.blurple()

    logger.info(
        "config.logging.update_moderation_access user=%s guild=%s option=%s role=%s",  # noqa: E501
        interaction.user.id,
        cast(Guild, interaction.guild).id,
        option,
        role.id,
    )

    return await interaction.response.send_message(
        embed=Embed(
            title="Moderation Configuration",
            description=desc,
            color=color,
        ),
        ephemeral=True,
    )


@moderation_group.command(name="update_ban_access")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.choices(
    option=[
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Remove", value="remove"),
    ]
)
@app_commands.describe(
    role="The role to update",
    option="Whether to add or remove the role from the ban access list",
)
async def update_ban_access(
    interaction: Interaction,
    role: discord.Role,
    option: Literal["add", "remove"],
) -> InteractionCallbackResponse:
    """Update the list of roles with ban access."""
    async with open_guild_config(
        cast(Nightcore, interaction.client),
        cast(Guild, interaction.guild).id,
    ) as guild_config:
        new_list, changed, state = update_id_list(
            guild_config.ban_access_roles_ids,
            role.id,
            option,
        )
        if changed:
            guild_config.ban_access_roles_ids = new_list

    if state == "exists":
        desc = f"Role <@&{role.id}> already in the ban access list."
        color = discord.Color.yellow()
    elif state == "absent":
        desc = f"Role <@&{role.id}> not in the ban access list."
        color = discord.Color.red()
    elif state == "added":
        desc = f"Role <@&{role.id}> added to the ban access list."
        color = discord.Color.blurple()
    else:  # removed
        desc = f"Role <@&{role.id}> removed from the ban access list."
        color = discord.Color.blurple()

    logger.info(
        "config.logging.update_ban_access user=%s guild=%s option=%s role=%s",
        interaction.user.id,
        cast(Guild, interaction.guild).id,
        option,
        role.id,
    )

    return await interaction.response.send_message(
        embed=Embed(
            title="Moderation Configuration",
            description=desc,
            color=color,
        ),
        ephemeral=True,
    )


@moderation_group.command(name="update_rr_access")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.choices(
    option=[
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Remove", value="remove"),
    ]
)
@app_commands.describe(
    role="The role to update",
    option="Whether to add or remove the role from the rr access list",
)
async def update_rr_access(
    interaction: Interaction,
    role: discord.Role,
    option: Literal["add", "remove"],
) -> InteractionCallbackResponse:
    """Update the list of leaders roles with `rr` access."""
    async with open_guild_config(
        cast(Nightcore, interaction.client),
        cast(Guild, interaction.guild).id,
    ) as guild_config:
        new_list, changed, state = update_id_list(
            guild_config.fraction_roles_access_roles_ids,
            role.id,
            option,
        )
        if changed:
            guild_config.fraction_roles_access_roles_ids = new_list

    if state == "exists":
        desc = f"Role <@&{role.id}> already in the rr access list."
        color = discord.Color.yellow()
    elif state == "absent":
        desc = f"Role <@&{role.id}> not in the rr access list."
        color = discord.Color.red()
    elif state == "added":
        desc = f"Role <@&{role.id}> added to the rr access list."
        color = discord.Color.blurple()
    else:  # removed
        desc = f"Role <@&{role.id}> removed from the rr access list."
        color = discord.Color.blurple()

    logger.info(
        "config.logging.update_rr_access user=%s guild=%s option=%s role=%s",
        interaction.user.id,
        cast(Guild, interaction.guild).id,
        option,
        role.id,
    )

    return await interaction.response.send_message(
        embed=Embed(
            title="Moderation Configuration",
            description=desc,
            color=color,
        ),
        ephemeral=True,
    )


@moderation_group.command(name="update_fraction_role_access")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.choices(
    option=[
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Remove", value="remove"),
    ]
)
@app_commands.describe(
    role="The role to update",
    option="Whether to add or remove the role from the fraction access list",
)
async def update_fraction_role_access(
    interaction: Interaction,
    role: discord.Role,
    option: Literal["add", "remove"],
) -> InteractionCallbackResponse:
    """Update the list of roles with `fraction_role` access."""
    async with open_guild_config(
        cast(Nightcore, interaction.client),
        cast(Guild, interaction.guild).id,
    ) as guild_config:
        new_list, changed, state = update_id_list(
            guild_config.leader_access_rr_roles_ids,
            role.id,
            option,
        )
        if changed:
            guild_config.leader_access_rr_roles_ids = new_list

    if state == "exists":
        desc = f"Role <@&{role.id}> already in the fraction access list."
        color = discord.Color.yellow()
    elif state == "absent":
        desc = f"Role <@&{role.id}> not in the fraction access list."
        color = discord.Color.red()
    elif state == "added":
        desc = f"Role <@&{role.id}> added to the fraction access list."
        color = discord.Color.blurple()
    else:  # removed
        desc = f"Role <@&{role.id}> removed from the fraction access list."
        color = discord.Color.blurple()

    logger.info(
        "config.logging.update_fraction_role_access user=%s guild=%s option=%s role=%s",  # noqa: E501
        interaction.user.id,
        cast(Guild, interaction.guild).id,
        option,
        role.id,
    )

    return await interaction.response.send_message(
        embed=Embed(
            title="Moderation Configuration",
            description=desc,
            color=color,
        ),
        ephemeral=True,
    )
