"""Command to check battlepass."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.models._enums import CaseDropTypeEnum
from src.infra.db.models.battlepass_level import BattlepassLevel
from src.infra.db.operations import (
    get_case_by_id,
    get_color_by_id,
    get_guild_battlepass_levels,
    get_or_create_user,
)
from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.features.economy.components.v2 import (
    BattlepassClaimViewV2,
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
        coin_name: str = "коинов"
        user_level: int = 0
        user_points: int = 0
        disable_button = False

        async with specified_guild_config(
            bot, guild.id, GuildEconomyConfig
        ) as (
            guild_config,
            session,
        ):
            coin_name = guild_config.coin_name or "коинов"

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

        reward_name = current_level.reward["name"]
        reward_type = current_level.reward["type"]
        reward_id = current_level.reward["drop_id"]
        reward_amount = current_level.reward["amount"]

        async with self.bot.uow.start() as session:
            match reward_type:
                case CaseDropTypeEnum.COINS.value:
                    reward_name = coin_name or "коины"
                case CaseDropTypeEnum.CASE.value:
                    case = await get_case_by_id(
                        session, guild_id=guild.id, case_id=reward_id
                    )

                    reward_name = case.name if case else "unknown"
                case CaseDropTypeEnum.COLOR.value:
                    color = await get_color_by_id(
                        session, guild_id=guild.id, color_id=reward_id
                    )

                    if color is None:
                        reward_name = "unknown"
                    else:
                        role = guild.get_role(color.role_id)

                        reward_name = role.name if role else "unknown"

                case _:
                    ...

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
