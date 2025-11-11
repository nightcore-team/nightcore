"""Command to check user's profile."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, User, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.operations import get_or_create_user
from src.nightcore.features.economy.components.v2 import UserProfileViewV2
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import format_voice_time

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


class Profile(Cog):
    def __init__(self, bot: "Nightcore"):
        self.bot = bot

    @app_commands.command(
        name="profile", description="Посмотреть профиль пользователя."
    )  # type: ignore
    @app_commands.describe(
        user="Пользователь, чей профиль нужно посмотреть. По умолчанию - вы сами."  # noqa: E501
    )
    @check_required_permissions(PermissionsFlagEnum.NONE)  # type: ignore
    async def profile(
        self, interaction: Interaction, user: User | None = None
    ):
        """Check user's profile."""

        guild = cast(Guild, interaction.guild)
        member = user or interaction.user

        async with specified_guild_config(
            self.bot,
            guild_id=guild.id,
            config_type=GuildEconomyConfig,
            _create=False,
        ) as (
            guild_config,
            session,
        ):
            coin_name = guild_config.coin_name

            user_record, _ = await get_or_create_user(
                session, guild_id=guild.id, user_id=member.id
            )

            drop_from_colors = guild_config.drop_from_colors_case or {}
            users_colors = [
                drop_from_colors[color_key]["role_id"]
                for color_key in user_record.inventory.get("colors", [])
                if color_key in drop_from_colors
            ]

        view = UserProfileViewV2(
            bot=self.bot,
            user_id=member.id,
            lvl=user_record.level,
            current_exp=user_record.current_exp,
            exp_to_lvl=user_record.exp_to_level,
            balance=user_record.coins,
            coin_name=coin_name,
            voice_activity=format_voice_time(user_record.voice_activity),
            messages_count=user_record.messages_count,
            avatar_url=member.display_avatar.url,
            cases=user_record.inventory.get("cases", {}),
            colors=users_colors,
        )

        await interaction.response.send_message(view=view, ephemeral=True)

        logger.info(
            "[command] - invoked user=%s guild=%s target_user=%s",
            interaction.user.id,
            guild.id,
            member.id,
        )


async def setup(bot: "Nightcore") -> None:
    """Setup the Profile cog."""
    await bot.add_cog(Profile(bot))
