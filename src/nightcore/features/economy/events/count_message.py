"""Handle count message events."""

import asyncio
import logging
from collections.abc import Awaitable, Sequence
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, Message, Role
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildLevelsConfig, GuildMultipliersConfig
from src.infra.db.models.configurations.levels import (
    GuildBonusRole,
)
from src.infra.db.operations import (
    get_guild_level,
    get_guild_level_role_ids,
    get_or_create_user,
    get_specified_guild_config,
)
from src.nightcore.utils import (
    ensure_messageable_channel_exists,
    ensure_role_exists,
    has_any_role_from_sequence,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.features.economy.components.v2.view.levelup import (
    LevelUpViewV2,
)
from src.nightcore.features.economy.utils import calculate_user_exp_to_level

logger = logging.getLogger(__name__)


class CountMessageEvent(Cog):
    def __init__(self, bot: "Nightcore"):
        self.bot = bot

    async def _handle_level_role(
        self,
        guild: Guild,
        member: Member,
        new_level: int,
        target_role_id: int,
        all_level_role_ids: Sequence[int],
    ) -> None:
        """Handle level role assignment/removal."""

        target_role = await ensure_role_exists(guild, target_role_id)
        if not target_role:
            logger.error(
                "[economy/levelup] Role %s not found in guild %s",
                target_role_id,
                guild.id,
            )
            return

        if target_role in member.roles:
            logger.info(
                "[economy/levelup] User %s already has role %s for level %s",
                member.id,
                target_role_id,
                new_level,
            )
            return

        try:
            # find user roles to remove
            roles_to_remove: list[Role | None] = cast(
                list[Role | None],
                has_any_role_from_sequence(
                    member,
                    all_level_role_ids,  # type: ignore
                    with_roles=True,
                ),
            )

            # remove all old roles
            if roles_to_remove:
                await member.remove_roles(
                    *[r for r in roles_to_remove if r is not None],
                    reason="Level role update",
                )
                logger.info(
                    "[economy/levelup] Removed old level roles %s from user %s",  # noqa: E501
                    [r.id for r in roles_to_remove if r is not None],
                    member.id,
                )

            # add new role
            await member.add_roles(
                target_role, reason=f"Reached level {new_level}"
            )
            logger.info(
                "[economy/levelup] Assigned role %s (level %s) to user %s in guild %s",  # noqa: E501
                target_role_id,
                new_level,
                member.id,
                guild.id,
            )

        except Exception as e:
            logger.exception(
                "[economy/levelup] Failed to update roles for user %s in guild %s: %s",  # noqa: E501
                member.id,
                guild.id,
                e,
            )

    async def _send_level_up_message(
        self,
        guild: Guild,
        notifications_channel_id: int,
        member: Member,
        new_level: int,
        exp_to_level: int,
    ) -> None:
        """Send level up notification message."""
        channel = await ensure_messageable_channel_exists(
            guild, notifications_channel_id
        )
        if not channel:
            logger.error(
                "[economy/levelup] Notifications channel %s not found in guild %s",  # noqa: E501
                notifications_channel_id,
                guild.id,
            )
            return

        view = LevelUpViewV2(self.bot, member.id, new_level, exp_to_level)

        try:
            await channel.send(view=view)  # type: ignore
        except Exception as e:
            logger.exception(
                "[economy/levelup] Failed to send level up message for user %s in guild %s: %s",  # noqa: E501
                member.id,
                guild.id,
                e,
            )
            return

    @Cog.listener()
    async def on_count_message(self, message: Message):
        """Handle count message events."""

        guild = cast(Guild, message.guild)
        author = cast(Member, message.author)

        is_level_up = False
        new_level_int = 0

        async with self.bot.uow.start() as session:
            multiplers_config = await get_specified_guild_config(
                session, config_type=GuildMultipliersConfig, guild_id=guild.id
            )
            levels_config = await get_specified_guild_config(
                session, config_type=GuildLevelsConfig, guild_id=guild.id
            )

            if multiplers_config is None or levels_config is None:
                return

            user, _ = await get_or_create_user(
                session,
                guild_id=guild.id,
                user_id=message.author.id,
            )

            user.messages_count += 1

            levelup_channel_id = levels_config.level_notify_channel_id

            exp_multiplier = (
                multiplers_config.temp_exp_multiplier
                or multiplers_config.base_exp_multiplier
            )
            coins_multiplier = (
                multiplers_config.temp_coins_multiplier
                or multiplers_config.base_coins_multiplier
            )
            battlepass_multiplier = (
                multiplers_config.temp_battlepass_multiplier
                or multiplers_config.base_battlepass_multiplier
            )

            # check bonus multiplier
            bonus_coins = 0
            bonus_roles: list[GuildBonusRole] = (
                levels_config.bonus_access_roles_ids
            )

            bonus_roles_int = [item.role_id for item in bonus_roles]

            if has_any_role_from_sequence(author, bonus_roles_int):
                user_bonus_roles = [
                    role_id
                    for role_id in bonus_roles
                    if role_id in [role.id for role in author.roles]
                ]

                if user_bonus_roles:
                    highest_bonus_role = max(
                        user_bonus_roles, key=lambda r: r.coins
                    )
                    bonus_coins += highest_bonus_role.coins

            # count user exp and coins
            new_current_exp = user.current_exp + exp_multiplier
            exp_to_level = 0

            # keep total exp; exp_to_level is the threshold for next level
            while new_current_exp >= user.exp_to_level:
                is_level_up = True
                new_level_int = user.level + 1
                user.level = new_level_int

                user.exp_to_level = calculate_user_exp_to_level(
                    new_level_int + 1
                )
                user.coins += coins_multiplier
                user.battle_pass_points += 100

            user.current_exp = new_current_exp
            if is_level_up:
                exp_to_level = user.exp_to_level - user.current_exp
            else:
                user.coins += coins_multiplier + bonus_coins
                user.battle_pass_points += battlepass_multiplier

            new_level = await get_guild_level(
                session, guild_id=guild.id, level=new_level_int
            )
            all_level_role_ids = await get_guild_level_role_ids(
                session, guild_id=guild.id
            )

        gather_list: list[Awaitable[None]] = []

        if is_level_up:
            logger.info(
                "[economy/levelup] User %s reached level %s in guild %s",
                author.id,
                new_level_int,
                guild.id,
            )

            if new_level is not None:
                gather_list.append(
                    self._handle_level_role(
                        guild=guild,
                        member=author,
                        new_level=new_level.level,
                        target_role_id=new_level.role_id,
                        all_level_role_ids=all_level_role_ids,
                    )
                )

            if levelup_channel_id:
                gather_list.append(
                    self._send_level_up_message(
                        guild=guild,
                        notifications_channel_id=levelup_channel_id,
                        member=author,
                        new_level=new_level_int,
                        exp_to_level=exp_to_level,
                    )
                )

        if gather_list:
            await asyncio.gather(*gather_list)
        else:
            logger.info(
                "[economy/levelup] No actions to perform for user %s in guild %s",  # noqa: E501
                author.id,
                guild.id,
            )

        logger.info(
            "[%s/log] - invoked user=%s guild=%s",
            "economy/levelup",
            author.id,
            guild.id,
        )


async def setup(bot: "Nightcore") -> None:
    """Setup the CountMessageEvent cog."""
    await bot.add_cog(CountMessageEvent(bot))
