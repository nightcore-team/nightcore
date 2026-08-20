"""Logging revision service implementation."""

import secrets
from typing import TYPE_CHECKING, Any, Final

import discord

from src.infra.db.models import LoggingRevision
from src.infra.db.operations import (
    get_last_logging_revision,
    get_logging_revision_by_id,
    get_logging_revisions,
)
from src.nightcore.api.endpoints.guild import LoggingRevisionDataSchema
from src.nightcore.api.schemas.logging_revision import (
    LoggingRevisionMetaSchema,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.infra.db.uow import UnitOfWork
    from src.utils._enums import ConfigTypeEnum


ALPHABET: Final[str] = (
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
)


class LoggingRevisionService:
    def __init__(self, uow: "UnitOfWork"):
        self._uow = uow

    def generate_revision_id(self, length: int = 12) -> str:
        """
        Generate a random revision ID using a base62 alphabet.

        Args:
            length: The length of the revision ID to generate.

        Returns:
            A string representing the generated revision ID.
        """

        return "".join(secrets.choice(ALPHABET) for _ in range(length))

    async def create_revision(
        self,
        session: "AsyncSession",
        *,
        guild_id: int,
        user_id: int,
        config_type: "ConfigTypeEnum",
        old_data: dict[str, Any],
        new_data: dict[str, Any],
    ):
        """
        Create a logging revision for a configuration change.

        Args:
            session: The async database session.
            guild_id: The ID of the guild where the change happened.
            user_id: The ID of the user who made the change.
            config_type: The type of the configuration that was changed.
            old_data: The previous configuration values.
            new_data: The updated configuration values.
        """

        revision_id = self.generate_revision_id()

        last_revision = await get_last_logging_revision(
            session, guild_id=guild_id
        )

        session.add(
            LoggingRevision(
                revision_id=revision_id,
                down_revision_id=last_revision.revision_id
                if last_revision
                else None,
                config_type=config_type,
                user_id=user_id,
                guild_id=guild_id,
                old_data=old_data,
                new_data=new_data,
            )
        )

    @staticmethod
    def _map_revision_to_schema(
        revision: LoggingRevision, members: dict[int, discord.Member]
    ) -> LoggingRevisionMetaSchema:
        """
        Map an ORM revision to its schema with the member display name.

        Args:
            revision: The ORM logging revision to map.
            members: A mapping of user IDs to guild members.

        Returns:
            A LoggingRevisionSchema representing the revision.
        """

        member = members.get(revision.user_id)

        return LoggingRevisionMetaSchema(
            revision_id=revision.revision_id,
            down_revision_id=revision.down_revision_id or "",
            config_type=revision.config_type,
            discord_user_id=revision.user_id,
            discord_username=member.display_name if member else "",
        )

    async def list_revisions_by_params(
        self,
        *,
        config_type: "ConfigTypeEnum",
        guild: discord.Guild,
        limit: int = 100,
        offset: int = 0,
    ) -> list[LoggingRevisionMetaSchema]:
        """
        Get logging revisions for a guild filtered by config type.

        Args:
            config_type: The type of the configuration to filter by.
            guild: The guild to get the revisions for.
            limit: The maximum number of revisions to return.
            offset: The number of revisions to skip.

        Returns:
            A list of LoggingRevisionSchema objects representing the
            most recent revisions.
        """

        async with self._uow.start() as session:
            revisions = await get_logging_revisions(
                session,
                guild_id=guild.id,
                config_type=config_type,
                limit=limit,
                offset=offset,
            )

        user_ids = [revision.user_id for revision in revisions]

        members: dict[int, discord.Member] = {}
        if user_ids:
            fetched = await guild.query_members(user_ids=user_ids, cache=True)
            members = {member.id: member for member in fetched}

        return [
            self._map_revision_to_schema(revision, members)
            for revision in revisions
        ]

    async def get_by_params(
        self, *, guild_id: int, revision_id: str, config_type: ConfigTypeEnum
    ) -> LoggingRevisionDataSchema:
        """
        Get a specific logging revision for a guild.

        Args:
            guild_id: The ID of the guild the revision belongs to.
            revision_id: The revision ID to look up.
            config_type: The type of the configuration the revision
                belongs to.

        Returns:
            A LoggingRevisionDataSchema containing the old and new data
            of the found revision (empty dicts when not found).
        """

        old_data = {}
        new_data = {}

        async with self._uow.start() as session:
            revision = await get_logging_revision_by_id(
                session,
                guild_id=guild_id,
                revision_id=revision_id,
                config_type=config_type,
            )

            if revision is not None:
                old_data = revision.old_data
                new_data = revision.new_data

        return LoggingRevisionDataSchema(
            revision_id=revision_id, old_data=old_data, new_data=new_data
        )
