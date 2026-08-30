"""Service for building and sending the battlepass claim view."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from discord import Guild

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.operations import (
    get_guild_battlepass_levels,
    get_or_create_user,
)
from src.nightcore.components.view.v2 import ErrorViewV2
from src.nightcore.features.economy.components.v2 import (
    BattlepassClaimViewV2,
)
from src.nightcore.features.economy.utils.case import (
    format_single_battlepass_level_reward,
)
from src.nightcore.services.config import specified_guild_config

if TYPE_CHECKING:
    from discord.interactions import Interaction

    from src.nightcore.bot import Nightcore


async def send_battlepass_claim_view(
    bot: Nightcore,
    interaction: Interaction[Nightcore],
    user_id: int | None = None,
) -> None:
    """Build and send the battlepass claim view for the user."""

    guild = cast(Guild, interaction.guild)
    target_user_id = user_id if user_id else interaction.user.id

    async with specified_guild_config(bot, guild.id, GuildEconomyConfig) as (
        guild_config,
        session,
    ):
        user_record, _ = await get_or_create_user(
            session,
            guild_id=guild.id,
            user_id=target_user_id,
            for_update=True,
        )

        user_level = user_record.battle_pass_level
        user_points = user_record.battle_pass_points

        battlepass_levels = await get_guild_battlepass_levels(
            session, guild_id=guild.id
        )

        if len(battlepass_levels) < 1:
            await interaction.response.send_message(
                view=ErrorViewV2(
                    "Ошибка получения уровня баттлпаса",
                    "Баттлпас не настроен на этом сервере.",
                ),
                ephemeral=True,
            )
            return

    level_index = user_level - 1
    disable_button = False

    if user_level > len(battlepass_levels):
        disable_button = True
        level_index = len(battlepass_levels) - 1

    current_level = battlepass_levels[level_index]

    async with bot.uow.start() as session:
        await format_single_battlepass_level_reward(
            session,
            level=current_level,
            coin_name=guild_config.coin_name,
            guild=guild,
        )

    reward_name = current_level.reward["name"]
    reward_amount = current_level.reward["amount"]

    target_member = guild.get_member(target_user_id) or bot.get_user(
        target_user_id
    )
    avatar_url = (
        target_member.display_avatar.url
        if target_member
        else interaction.user.display_avatar.url
    )

    view = BattlepassClaimViewV2(
        bot=bot,
        level=user_level,
        total_levels=len(battlepass_levels),
        current_points=user_points,
        required_points=current_level.exp_required,
        reward_type=reward_name,
        reward_amount=reward_amount,
        avatar_url=avatar_url,
        disable_button=disable_button,
    )

    await interaction.response.send_message(
        view=view,
        ephemeral=True,
    )
