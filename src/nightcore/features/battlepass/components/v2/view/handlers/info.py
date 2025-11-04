"""
Battlepass info button handler.

Handles displaying battlepass information.
"""

from typing import TYPE_CHECKING, cast

from discord import Guild
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.operations import get_or_create_user
from src.nightcore.features.battlepass.utils.pages import (
    build_battlepass_levels_pages,
)
from src.nightcore.services.config import specified_guild_config

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

    from ..info import BattlepassInfoViewV2


async def handle_battlepass_info_button(
    interaction: Interaction["Nightcore"], view: type["BattlepassInfoViewV2"]
) -> None:
    """Handle battlepass info button."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    async with specified_guild_config(bot, guild.id, GuildEconomyConfig) as (
        guild_config,
        session,
    ):
        user_record, _ = await get_or_create_user(
            session,
            guild_id=guild.id,
            user_id=interaction.user.id,
        )

        coin_name = guild_config.coin_name
        user_level = user_record.battle_pass_level

        battlepass_rewards = guild_config.battlepass_rewards or []
        total_bp_points = sum(
            [level["exp_required"] for level in battlepass_rewards]
        )

    pages = build_battlepass_levels_pages(
        levels=battlepass_rewards,
        coin_name=coin_name,
        current_user_level=user_level,
        is_v2=True,
    )

    _view = view(
        bot=bot,
        user_level=user_level,
        total_bp_levels=len(battlepass_rewards),
        total_bp_points=total_bp_points,
        pages=pages,
    )

    await interaction.response.send_message(view=_view, ephemeral=True)
