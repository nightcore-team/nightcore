"""Moderstats configuration commands for the Nightcore bot."""

import logging
from typing import cast

import discord
from discord import Guild, app_commands
from discord.embeds import Embed
from discord.interactions import Interaction

from src.infra.db.models.guild import GuildTicketsConfig
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import NoOptionsSuppliedEmbed
from src.nightcore.features.config._groups import config as main_config_group
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.field_validators import (
    FieldSpec,
    apply_field_changes,
    format_changes,
    int_id_value,
    split_changes,
)

logger = logging.getLogger(__name__)


@main_config_group.command(
    name="tickets", description="Configure tickets settings."
)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    new_tickets_category="The category for new tickets",
    pinned_tickets_category="The category for pinned tickets",
    closed_tickets_category="The category for closed tickets",
    create_ticket_channel="The channel for creating tickets",
    create_ticket_ping_role="The role to ping when a ticket is created",
)
async def tickets(
    interaction: Interaction,
    new_tickets_category: discord.CategoryChannel | None = None,
    pinned_tickets_category: discord.CategoryChannel | None = None,
    closed_tickets_category: discord.CategoryChannel | None = None,
    create_ticket_channel: discord.TextChannel | None = None,
    create_ticket_ping_role: discord.Role | None = None,
):
    """Configure tickets settings."""

    specs: list[FieldSpec | None] = [
        int_id_value("new_tickets_category_id", new_tickets_category),
        int_id_value("pinned_tickets_category_id", pinned_tickets_category),
        int_id_value("closed_tickets_category_id", closed_tickets_category),
        int_id_value("create_ticket_channel_id", create_ticket_channel),
        int_id_value("create_ticket_ping_role_id", create_ticket_ping_role),
    ]

    specs = [s for s in specs if s is not None]

    if not specs:
        logger.info(
            "config.tickets invoked user=%s guild=%s no_options_supplied",
            interaction.user.id,  # type: ignore
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
        config_type=GuildTicketsConfig,
    ) as guild_config:
        changes = apply_field_changes(guild_config, specs)  # type: ignore

    changed, skipped = split_changes(changes)
    description = format_changes(changed, skipped)

    logger.info(
        "config.tickets invoked user=%s guild=%s updated=%s skipped=%s",
        interaction.user.id,
        cast(Guild, interaction.guild).id,
        changed,
        skipped,
    )
    return await interaction.response.send_message(
        embed=Embed(
            title="Tickets Configuration",
            description=description,
            color=discord.Color.green(),
        ),
        ephemeral=True,
    )
