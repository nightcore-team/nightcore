"""Guild state service implementation."""

from collections.abc import Sequence
from typing import Any

import discord

from src.infra.db.operations import (
    CONFIG_MODEL_MAP,
    get_specified_guild_config,
)
from src.infra.db.uow import UnitOfWork
from src.nightcore.api.domain.exceptions.base import LogicalError
from src.nightcore.api.schemas.configuration import (
    CONFIG_SCHEMA_MODEL_MAP,
)
from src.nightcore.api.schemas.guild import ChannelInfoSchema, RoleInfoSchema
from src.nightcore.api.utils.validators import (
    ChannelInfo,
    RoleInfo,
    ValidationContext,
)
from src.nightcore.bot import Nightcore
from src.utils._enums import ConfigTypeEnum


class GuildStateService:
    def __init__(self, uow: UnitOfWork, bot: Nightcore) -> None:
        self._bot = bot
        self._uow = uow

    async def _build_validation_context(
        self, guild: discord.Guild
    ) -> ValidationContext:
        roles_dict = {
            role.id: RoleInfo(
                administrator=role.permissions.administrator,
            )
            for role in guild.roles
        }

        channels_dict = {
            channel.id: ChannelInfo(
                type=channel.type.name,
            )
            for channel in guild.channels
        }

        return ValidationContext(
            guild_id=guild.id,
            roles=roles_dict,
            channels=channels_dict,
        )

    def get_roles(self, guild: discord.Guild) -> Sequence[RoleInfoSchema]:
        """
        Get the roles of a guild.

        Args:
            guild: The guild to get the roles from.

        Returns:
            A list of RoleInfoSchema objects representing the roles of the guild.
        """  # noqa: E501

        return [RoleInfoSchema.from_discord(role) for role in guild.roles]

    def get_channels(self, guild: discord.Guild) -> list[ChannelInfoSchema]:
        """
        Get the channels of a guild.

        Args:
            guild: The guild to get the channels from.

        Returns:
            A list of ChannelInfoSchema objects representing the channels of the guild.
        """  # noqa: E501

        return [
            ChannelInfoSchema.from_discord(channel)
            for channel in guild.channels
        ]

    def get_member(
        self, guild: discord.Guild, user_id: int
    ) -> discord.Member | None:
        """
        Get a member of a guild by their user ID.

        Args:
            guild: The guild to get the member from.
            user_id: The ID of the user to get the member for.

        Returns:
            A discord.Member object representing the member, or None if the member is not found.

        """  # noqa: E501

        return guild.get_member(user_id)

    async def get_config(
        self, guild: discord.Guild, config_type: ConfigTypeEnum
    ) -> dict[str, Any]:
        """
        Get the configuration of a guild.

        Args:
            guild: The guild to get the configuration from.
            config_type: The type of the configuration to get.

        Returns:
            A dictionary representing the configuration of the guild.
        """

        type_ = CONFIG_MODEL_MAP.get(config_type)

        if type_ is None:
            raise LogicalError("Unknown config type")

        async with self._uow.start() as session:
            config = await get_specified_guild_config(
                session,
                config_type=type_,
                guild_id=guild.id,
            )

        pydantic_type = CONFIG_SCHEMA_MODEL_MAP.get(config_type)

        if pydantic_type is None:
            raise LogicalError("Pydantic model not found for this config type")

        return pydantic_type.model_construct(**vars(config)).model_dump(
            mode="json"
        )

    async def update_config(
        self,
        guild: discord.Guild,
        config_type: ConfigTypeEnum,
        data: dict[str, Any],
    ):
        """
        Update the configuration of a guild.

        Args:
            guild: The guild to update the configuration for.
            config_type: The type of the configuration to update.
            data: A dictionary representing the new configuration data.

        Raises:
            ValueError: If the config type is unknown.
            LogicalError: If the pydantic model for the config type is not found.
        """  # noqa: E501

        type_ = CONFIG_MODEL_MAP.get(config_type)

        if type_ is None:
            raise ValueError("Unknown config type")

        pydantic_type = CONFIG_SCHEMA_MODEL_MAP.get(config_type)

        if pydantic_type is None:
            raise LogicalError("Pydantic model not found for this config type")

        context = await self._build_validation_context(guild)
        validated_model = pydantic_type.model_validate(data, context=context)

        dump = validated_model.model_dump(exclude_unset=True)

        nomalized = type_.normalize_from_json(dump)

        async with self._uow.start() as session:
            config = await get_specified_guild_config(
                session,
                config_type=type_,
                guild_id=guild.id,
            )

            for k, v in nomalized.items():
                setattr(config, k, v)
