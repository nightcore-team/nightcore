"""Handle count message events."""

import asyncio
import logging
from collections.abc import Awaitable
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, Message, Role
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildLevelsConfig
from src.infra.db.operations import get_or_create_user
from src.nightcore.services.config import specified_guild_config
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

    def _get_role_for_level(
        self,
        level: int,
        level_roles: dict[str, int],
    ) -> int | None:
        """Get role ID for current level."""
        if not level_roles:
            return None

        if str(level) in level_roles:
            return level_roles[str(level)]

        available_levels = sorted(map(int, level_roles))
        suitable_levels = [lvl for lvl in available_levels if lvl <= level]

        if not suitable_levels:
            return None

        closest_level = max(suitable_levels)
        return level_roles[str(closest_level)]

    async def _handle_level_role(
        self,
        guild: Guild,
        member: Member,
        new_level: int,
        level_roles: dict[str, int],
    ) -> None:
        """Handle level role assignment/removal."""

        if not level_roles:
            logger.info(
                "[economy/levelup] No level roles configured for guild %s",
                guild.id,
            )
            return

        target_role_id = self._get_role_for_level(new_level, level_roles)

        if not target_role_id:
            logger.info(
                "[economy/levelup] No role available for level %s in guild %s",
                new_level,
                guild.id,
            )
            return

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
            all_level_role_ids = set(level_roles.values())

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
        new_level = 0

        async with specified_guild_config(
            self.bot, guild.id, config_type=GuildLevelsConfig
        ) as (guild_config, session):
            user, _ = await get_or_create_user(
                session,
                guild_id=guild.id,
                user_id=message.author.id,
            )

            user.messages_count += 1

            levelup_channel_id = guild_config.level_notify_channel_id

            if t := guild_config.temp_exp_multiplier:
                exp_multiplier = t
            else:
                exp_multiplier = guild_config.base_exp_multiplier

            if c := guild_config.temp_coins_multiplier:
                coins_multiplier = c
            else:
                coins_multiplier = guild_config.base_coins_multiplier

            # check bonus multiplier
            bonus_multiplier = 1
            bonus_roles: dict[int, int] = guild_config.bonus_access_roles_ids

            if has_any_role_from_sequence(author, list(map(int, bonus_roles))):
                bonus_roles_int = {int(k): v for k, v in bonus_roles.items()}

                user_bonus_roles = [
                    role_id
                    for role_id in bonus_roles_int
                    if role_id in [role.id for role in author.roles]
                ]

                if user_bonus_roles:
                    highest_bonus_role_id = max(
                        user_bonus_roles, key=lambda r: bonus_roles_int[r]
                    )
                    bonus_multiplier += bonus_roles_int[highest_bonus_role_id]

            exp_multiplier *= bonus_multiplier
            coins_multiplier *= bonus_multiplier

            # count user exp and coins
            new_current_exp = user.current_exp + exp_multiplier
            exp_to_level = 0
            if new_current_exp >= user.exp_to_level:
                is_level_up = True
                new_level = user.level + 1
                user.level = new_level

                new_exp_to_level = calculate_user_exp_to_level(new_level + 1)

                user.exp_to_level = new_exp_to_level
                user.coins += coins_multiplier
                user.battle_pass_points += 100
                exp_to_level = +(new_exp_to_level - new_current_exp)
            else:
                user.current_exp = new_current_exp
                user.coins += coins_multiplier
                user.battle_pass_points += 8

            level_roles = guild_config.level_roles

        gather_list: list[Awaitable[None]] = []

        if is_level_up:
            logger.info(
                "[economy/levelup] User %s reached level %s in guild %s",
                author.id,
                new_level,
                guild.id,
            )

            gather_list.append(
                self._handle_level_role(
                    guild=guild,
                    member=author,
                    new_level=new_level,
                    level_roles=level_roles,
                )
            )

            if levelup_channel_id:
                gather_list.append(
                    self._send_level_up_message(
                        guild=guild,
                        notifications_channel_id=levelup_channel_id,
                        member=author,
                        new_level=new_level,
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
