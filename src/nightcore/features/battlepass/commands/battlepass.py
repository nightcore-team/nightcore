"""Command to check battlepass."""

from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.models._annot import BattlepassLevelAnnot
from src.infra.db.operations import get_or_create_user
from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.features.battlepass.components.v2 import (
    BattlepassClaimViewV2,
)
from src.nightcore.features.battlepass.utils.types import BATTLEPASS_REWARDS
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class Battlepass(Cog):
    """Battlepass commands."""

    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(  # type: ignore
        name="battlepass",
        description="Взаимодействие с баттлпасом сервера.",
    )
    @check_required_permissions(PermissionsFlagEnum.NONE)  # type: ignore
    async def claim(self, interaction: Interaction["Nightcore"]):
        """Claim your battlepass rewards."""

        bot = self.bot
        guild = cast(Guild, interaction.guild)

        outcome = ""
        current_level: BattlepassLevelAnnot | None = None
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

        battlepass_rewards = guild_config.battlepass_rewards or []

        if not battlepass_rewards:
            outcome = "battlepass_not_configured"
        else:
            for bp_level in battlepass_rewards:
                if bp_level["level"] == user_level:
                    current_level = bp_level
                    break
            else:
                previous_levels = [
                    bp for bp in battlepass_rewards if bp["level"] < user_level
                ]
                if previous_levels:
                    current_level = max(
                        previous_levels, key=lambda x: x["level"]
                    )
                    disable_button = True

        if outcome == "battlepass_not_configured":
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка получения уровня баттлпаса",
                    "Баттлпас не настроен на этом сервере.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        # If level not found and no previous levels available
        if current_level is None:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка получения уровня баттлпаса",
                    "Ваш уровень превышает все настроенные уровни баттлпаса, "
                    "или у вас еще нет доступных уровней.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        reward_type = BATTLEPASS_REWARDS[current_level["reward"]["name"]]
        reward_amount = current_level["reward"]["amount"]

        if reward_type == "коины":
            reward_type = coin_name or "коины"

        view = BattlepassClaimViewV2(
            bot=bot,
            level=user_level,
            total_levels=len(battlepass_rewards),
            current_points=user_points,
            required_points=current_level["exp_required"],
            reward_type=reward_type,
            reward_amount=reward_amount,
            avatar_url=interaction.user.display_avatar.url,
            disable_button=disable_button,
        )

        await interaction.response.send_message(
            view=view,
            ephemeral=True,
        )


async def setup(bot: "Nightcore") -> None:
    """Setup the Battlepass cog."""
    await bot.add_cog(Battlepass(bot))
