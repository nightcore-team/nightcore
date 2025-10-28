"""Economy configuration command for Nightcore bot."""

import logging
from typing import Literal, cast

import discord
from discord import Guild, app_commands
from discord.embeds import Embed
from discord.interactions import Interaction

from src.infra.db.models.guild import GuildEconomyConfig
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import NoOptionsSuppliedEmbed
from src.nightcore.features.config._groups import economy as economy_group
from src.nightcore.features.config.utils import shop_items_dict_value
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.field_validators import (
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


@economy_group.command(name="setup", description="Configure economy settings.")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    shop_buy_ping_roles="Roles to ping when buying from the shop.",
    economy_access_roles="Roles that have access to economy commands.",
    # cases_drop="Drop from cases.",
    shop_items="Items available in the shop.",
    reward_bonus="Bonus rewards for /reward.",
    coin_name="Name of the local currency.",
    # colors="...",
)
async def setup(
    interaction: Interaction,
    shop_buy_ping_roles: str | None = None,
    economy_access_roles: str | None = None,
    # cases_drop: str | None = None,
    economy_shop: discord.TextChannel | None = None,
    shop_items: str | None = None,
    reward_bonus: int | None = None,
    coin_name: str | None = None,
    # colors: str | None = None,
):
    """Configure economy settings."""

    specs: list[FieldSpec | None] = [
        list_csv("economy_shop_buy_ping_roles_ids", shop_buy_ping_roles),
        list_csv("economy_access_roles_ids", economy_access_roles),
        shop_items_dict_value("economy_shop_items", shop_items),
        int_id_value("economy_shop_channel_id", economy_shop),
        int_id_value("reward_bonus", reward_bonus),
        str_value("coin_name", coin_name),
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
        config_type=GuildEconomyConfig,
    ) as (guild_config, _):
        changes = apply_field_changes(guild_config, specs)  # type: ignore

    changed, skipped = split_changes(changes)
    description = format_changes(changed, skipped)

    await interaction.response.send_message(
        embed=Embed(
            title="Economy Configuration",
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


@economy_group.command(name="update_economy_access")
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
async def update_economy_access(
    interaction: Interaction,
    role: discord.Role,
    option: Literal["add", "remove"],
):
    """Update the list of roles with `economy` access."""
    async with specified_guild_config(
        cast(Nightcore, interaction.client),
        cast(Guild, interaction.guild).id,
        config_type=GuildEconomyConfig,
    ) as (guild_config, _):
        new_list, changed, state = update_id_list(
            guild_config.economy_access_roles_ids,
            role.id,
            option,
        )
        if changed:
            guild_config.economy_access_roles_ids = new_list

    if state == "exists":
        desc = f"Role <@&{role.id}> already in the economy access list."
        color = discord.Color.yellow()
    elif state == "absent":
        desc = f"Role <@&{role.id}> not in the economy access list."
        color = discord.Color.red()
    elif state == "added":
        desc = f"Role <@&{role.id}> added to the economy access list."
        color = discord.Color.blurple()
    else:  # removed
        desc = f"Role <@&{role.id}> removed from the economy access list."
        color = discord.Color.blurple()

    await interaction.response.send_message(
        embed=Embed(
            title="Economy Configuration",
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
