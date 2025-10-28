"""Economy configuration command for Nightcore bot."""

import logging
from typing import Literal, cast

import discord
from discord import Guild, app_commands
from discord.embeds import Embed
from discord.interactions import Interaction

from src.infra.db.models.guild import GuildClansConfig
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import NoOptionsSuppliedEmbed
from src.nightcore.features.config._groups import clans as clans_group
from src.nightcore.features.config.utils import shop_items_dict_value
from src.nightcore.services.config import specified_guild_config
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


@clans_group.command(name="setup", description="Configure clans settings.")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    shop_threads_channel="Channel for shop threads.",
    shop_buy_ping_roles="Roles to ping when buying from the shop. (str, str, str)",  # noqa: E501
    shop_items="Items available in the shop. (str, int | str, int)",
    reputation_per_payday="Reputation points awarded per payday. int",
    payday_channel="Channel for payday announcements.",
    base_exp_multiplier="Reputation points awarded per message. int",
    improvements_costs="Costs for clan improvements (int, int, int).",
)
async def setup(
    interaction: Interaction,
    shop_threads_channel: discord.TextChannel | None = None,
    shop_buy_ping_roles: str | None = None,
    shop_items: str | None = None,
    reputation_per_payday: int | None = None,
    base_exp_multiplier: int | None = None,
    payday_channel: discord.TextChannel | None = None,
    improvements_costs: str | None = None,
):
    """Configure clans settings."""

    # TODO: change clan_reputation_per_messsage to base_exp_multiplier
    specs: list[FieldSpec | None] = [
        int_id_value("clan_shop_channel_id", shop_threads_channel),
        list_csv("clan_buy_ping_roles_ids", shop_buy_ping_roles),
        shop_items_dict_value("clan_shop_items", shop_items),
        int_id_value("clan_reputation_per_payday", reputation_per_payday),
        int_id_value("clan_reputation_per_message", base_exp_multiplier),
        int_id_value("clan_payday_channel_id", payday_channel),
        list_csv("clan_improvements", improvements_costs, _len=3),
    ]

    specs = [s for s in specs if s is not None]

    if not specs:
        logger.info(
            "[command] - invoked user=%s guild=%s no_options_supplied",
            interaction.user.id,
            cast(Guild, interaction.guild).id,
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
        config_type=GuildClansConfig,
    ) as (guild_config, _):
        changes = apply_field_changes(guild_config, specs)  # type: ignore

    changed, skipped = split_changes(changes)
    description = format_changes(changed, skipped)

    await interaction.response.send_message(
        embed=Embed(
            title="Clans Configuration",
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


@clans_group.command(name="update_clans_access")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.choices(
    option=[
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Remove", value="remove"),
    ]
)
@app_commands.describe(
    role="The role to update",
    option="Whether to add or remove the role from the clans access list.",
)
async def update_clans_access(
    interaction: Interaction,
    role: discord.Role,
    option: Literal["add", "remove"],
):
    """Update the list of roles with `clans` access."""
    async with specified_guild_config(
        cast(Nightcore, interaction.client),
        cast(Guild, interaction.guild).id,
        config_type=GuildClansConfig,
    ) as (guild_config, _):
        new_list, changed, state = update_id_list(
            guild_config.clans_access_roles_ids,
            role.id,
            option,
        )
        if changed:
            guild_config.clans_access_roles_ids = new_list

    if state == "exists":
        desc = f"Role <@&{role.id}> already in the clans access list."
        color = discord.Color.yellow()
    elif state == "absent":
        desc = f"Role <@&{role.id}> not in the clans access list."
        color = discord.Color.red()
    elif state == "added":
        desc = f"Role <@&{role.id}> added to the clans access list."
        color = discord.Color.blurple()
    else:  # removed
        desc = f"Role <@&{role.id}> removed from the clans access list."
        color = discord.Color.blurple()

    await interaction.response.send_message(
        embed=Embed(
            title="Clans Configuration",
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
