"""Main configuration command for Nightcore bot."""

import logging
from typing import Literal, cast

import discord
from discord import Guild, app_commands
from discord.embeds import Embed
from discord.interactions import Interaction

from src.infra.db.models.guild import MainGuildConfig
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import NoOptionsSuppliedEmbed
from src.nightcore.features.config._groups import main as main_group
from src.nightcore.features.config.utils import (
    org_roles_dict_value,
    temp_voice_roles_dict_value,
)
from src.nightcore.services.config import (
    specified_guild_config,
)
from src.nightcore.utils.field_validators import (
    FieldSpec,
    apply_field_changes,
    format_changes,
    int_id_value,
    list_csv,
    split_changes,
    update_id_list,
)

logger = logging.getLogger(__name__)


@main_group.command(name="setup", description="Configure main settings.")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    rules_channel="The channel for rules",
    proposal_channel="The channel for proposals",
    organizational_roles="The roles for the organizations",
    fraction_roles="The roles for the fractions",
    voice_temp_roles="The roles for the voice temp rooms",
    # faq=""
)
async def setup(
    interaction: Interaction,
    rules_channel: discord.TextChannel | None = None,  #
    proposal_channel: discord.TextChannel | None = None,  #
    voice_temp_roles: str | None = None,  #
    organizational_roles: str | None = None,  #
    fraction_roles: str | None = None,  #
    # faq: str | None = None, #
    role_request_channel: discord.TextChannel | None = None,  #
):
    """Configure moderation settings."""

    specs: list[FieldSpec | None] = [
        int_id_value("rules_channel_id", rules_channel),
        int_id_value("create_proposal_channel_id", proposal_channel),
        org_roles_dict_value("organizational_roles", organizational_roles),
        temp_voice_roles_dict_value("voice_temp_roles", voice_temp_roles),
        list_csv("fraction_roles", fraction_roles),
    ]

    specs = [s for s in specs if s is not None]

    if not specs:
        logger.info(
            "[command] - invoked user=%s guild=%s no_options_supplied",
            interaction.user.id,
            interaction.guild.id,  # type: ignore
        )
        return await interaction.response.send_message(
            embed=NoOptionsSuppliedEmbed(
                interaction.client.user.name,  # type: ignore
                interaction.client.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    async with specified_guild_config(
        cast(Nightcore, interaction.client),
        cast(Guild, interaction.guild).id,
        config_type=MainGuildConfig,
    ) as guild_config:
        changes = apply_field_changes(guild_config, specs)  # type: ignore

    changed, skipped = split_changes(changes)
    description = format_changes(changed, skipped)

    await interaction.response.send_message(
        embed=Embed(
            title="Main Configuration",
            description=description,
            color=discord.Color.green(),
        ),
        ephemeral=True,
    )

    logger.info(
        "[command] - invoked user=%s guild=%s updated=%s skipped=%s",
        interaction.user.id,
        cast(Guild, interaction.guild).id,
        changed,
        skipped,
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
    option="Whether to add or remove the role from the fraction roles list",
)
async def update_fraction_roles(
    interaction: Interaction,
    role: discord.Role,
    option: Literal["add", "remove"],
):
    """Update the list of roles with ban access."""
    async with specified_guild_config(
        cast(Nightcore, interaction.client),
        cast(Guild, interaction.guild).id,
        config_type=MainGuildConfig,
    ) as guild_config:
        new_list, changed, state = update_id_list(
            guild_config.fraction_roles,
            role.id,
            option,
        )
        if changed:
            guild_config.fraction_roles = new_list

    if state == "exists":
        desc = f"Role <@&{role.id}> already in the fraction roles list."
        color = discord.Color.yellow()
    elif state == "absent":
        desc = f"Role <@&{role.id}> not in the fraction roles list."
        color = discord.Color.red()
    elif state == "added":
        desc = f"Role <@&{role.id}> added to the fraction roles list."
        color = discord.Color.blurple()
    else:  # removed
        desc = f"Role <@&{role.id}> removed from the fraction roles list."
        color = discord.Color.blurple()

    await interaction.response.send_message(
        embed=Embed(
            title="Main Configuration",
            description=desc,
            color=color,
        ),
        ephemeral=True,
    )

    logger.info(
        "[command] - invoked user=%s guild=%s option=%s role=%s",
        interaction.user.id,
        cast(Guild, interaction.guild).id,
        option,
        role.id,
    )
