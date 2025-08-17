"""Main configuration command for Nightcore bot."""

import logging
from typing import Literal, cast

import discord
from discord import Guild, app_commands
from discord.embeds import Embed
from discord.interactions import Interaction, InteractionCallbackResponse

from src.nightcore.bot import Nightcore
from src.nightcore.commands.config._groups import main as main_group
from src.nightcore.components.embed.error import NoOptionsSuppliedEmbed
from src.nightcore.services.config import open_guild_config
from src.nightcore.utils.config_commands import (
    FieldSpec,
    apply_field_changes,
    format_changes,
    int_id_value,
    list_csv,
    roles_dict_value,
    split_changes,
)
from src.nightcore.utils.config_commands.helper import update_id_list

logger = logging.getLogger(__name__)


@main_group.command(name="setup", description="Configure main settings.")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    rules_channel="The channel for rules",
    proposal_channel="The channel for proposals",
    organizational_roles="The roles for the organizations",
    fraction_roles="The roles for the fractions",
    nightcore_notifications_channel="The channel for Nightcore notifications",
)
async def setup(
    interaction: Interaction,
    rules_channel: discord.TextChannel | None = None,
    proposal_channel: discord.TextChannel | None = None,
    nightcore_notifications_channel: discord.TextChannel | None = None,
    organizational_roles: str | None = None,
    fraction_roles: str | None = None,
) -> InteractionCallbackResponse:
    """Configure moderation settings."""

    specs: list[FieldSpec | None] = [
        int_id_value("rules_channel_id", rules_channel),
        int_id_value("create_proposal_channel_id", proposal_channel),
        int_id_value(
            "notifications_from_bot_channel_id",
            nightcore_notifications_channel,
        ),
        roles_dict_value("organizational_roles", organizational_roles),
        list_csv("fraction_roles", fraction_roles),
    ]

    specs = [s for s in specs if s is not None]

    if not specs:
        logger.info(
            "config.main invoked user=%s guild=%s no_options_supplied",
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
        "config.main invoked user=%s guild=%s updated=%s skipped=%s",
        interaction.user.id,
        cast(Guild, interaction.guild).id,
        changed,
        skipped,
    )
    return await interaction.response.send_message(
        embed=Embed(
            title="Main Configuration",
            description=description,
            color=discord.Color.green(),
        ),
        ephemeral=True,
    )


@main_group.command(
    name="update_fraction_roles", description="Update the fraction roles."
)
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
async def update_fraction_roles(
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
            guild_config.fraction_roles,
            role.id,
            option,
        )
        if changed:
            guild_config.fraction_roles = new_list

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
