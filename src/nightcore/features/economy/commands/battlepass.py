"""Command to check battlepass."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.models.battlepass_level import BattlepassLevel
from src.infra.db.operations import (
    get_guild_battlepass_levels,
    get_or_create_user,
)
from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.features.economy.components.v2 import (
    BattlepassClaimViewV2,
)
from src.nightcore.features.economy.utils.case import (
    format_single_battlepass_level_reward,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class Battlepass(Cog):
    """Battlepass commands."""

    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(  # type: ignore
        name="battlepass",
        description="Взаимодействие с баттлпасом сервера.",
    )
    @app_commands.guild_only()
    @check_required_permissions(PermissionsFlagEnum.NONE)  # type: ignore
    async def claim(self, interaction: Interaction[Nightcore]):
        """Claim your battlepass rewards."""

        bot = self.bot
        guild = cast(Guild, interaction.guild)

        current_level: BattlepassLevel | None = None
        user_level: int = 0
        user_points: int = 0
        disable_button = False

        async with specified_guild_config(
            bot, guild.id, GuildEconomyConfig
        ) as (
            guild_config,
            session,
        ):
            user_record, _ = await get_or_create_user(
                session,
                guild_id=guild.id,
                user_id=interaction.user.id,
            )

            user_level = user_record.battle_pass_level
            user_points = user_record.battle_pass_points

            battlepass_levels = await get_guild_battlepass_levels(
                session, guild_id=guild.id
            )

        if len(battlepass_levels) < 1:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка получения уровня баттлпаса",
                    "Баттлпас не настроен на этом сервере.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        level_index = user_level - 1

        if user_level > len(battlepass_levels):
            disable_button = True
            level_index = len(battlepass_levels) - 1

        current_level = battlepass_levels[level_index]

        async with self.bot.uow.start() as session:
            await format_single_battlepass_level_reward(
                session,
                level=current_level,
                coin_name=guild_config.coin_name,
                guild=guild,
            )

        reward_name = current_level.reward["name"]
        reward_amount = current_level.reward["amount"]

        view = BattlepassClaimViewV2(
            bot=bot,
            level=user_level,
            total_levels=len(battlepass_levels),
            current_points=user_points,
            required_points=current_level.exp_required,
            reward_type=reward_name,
            reward_amount=reward_amount,
            avatar_url=interaction.user.display_avatar.url,
            disable_button=disable_button,
        )

        await interaction.response.send_message(
            view=view,
            ephemeral=True,
        )


async def setup(bot: Nightcore) -> None:
    """Setup the Battlepass cog."""
    await bot.add_cog(Battlepass(bot))
