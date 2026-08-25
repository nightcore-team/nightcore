"""Access service implementation."""

import discord

from src.infra.db.operations import (
    get_available_guild_configs,
    has_guild_config_access,
)
from src.infra.db.uow import UnitOfWork
from src.nightcore.api.schemas.guild import GuildInfoSchema
from src.nightcore.bot import Nightcore
from src.utils._enums import ConfigTypeEnum


class AccessService:
    def __init__(
        self,
        bot: Nightcore,
        uow: UnitOfWork,
    ) -> None:
        self._bot = bot
        self._uow = uow

    def get_user_guilds(self, user_id: int) -> list[GuildInfoSchema]:
        """
        Get the guilds that a user is a member of.

        Args:
            user_id: The ID of the user to get the guilds for.

        Returns:
            A list of GuildInfoSchema objects representing the guilds that the user is a member of.
        """  # noqa: E501

        return [
            GuildInfoSchema.from_discord(guild)
            for guild in self._bot.guilds
            if guild.get_member(user_id) is not None
        ]

    def _has_administrator_access(
        self,
        member: discord.Member,
    ) -> bool:
        return member.guild_permissions.administrator

    async def get_available_configurations(
        self, member: discord.Member
    ) -> list[str]:
        """
        Get the available configurations for a user in a guild.

        Args:
            member: The member to get the available configurations for.

        Returns:
            A list of strings representing the available configurations.
        """

        async with self._uow.start() as session:
            configurations = await get_available_guild_configs(
                session,
                guild_id=member.guild.id,
                roles=[role.id for role in member.roles],
            )

        if self._has_administrator_access(member=member):
            configurations.append(ConfigTypeEnum.ACCESS.value)

        return configurations

    async def has_config_access(
        self,
        member: discord.Member,
        config_type: ConfigTypeEnum,
    ) -> bool:
        """
        Check if a user has access to a specific configuration in a guild.

        Args:
            member: The member to check the access for.
            config_type: The type of the configuration to check access for.

        Returns:
            A boolean indicating whether the user has access to the configuration.
        """  # noqa: E501

        if config_type == ConfigTypeEnum.ACCESS:
            return self._has_administrator_access(member=member)

        async with self._uow.start() as session:
            return await has_guild_config_access(
                session,
                guild_id=member.guild.id,
                roles=[role.id for role in member.roles],
                config_type=config_type,
            )
