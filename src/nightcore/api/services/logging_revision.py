"""Logging revision service implementation."""

import secrets
from datetime import datetime
from typing import TYPE_CHECKING, Any, Final

import discord

from src.infra.db.models import LoggingRevision
from src.infra.db.operations import (
    CONFIG_MODEL_MAP,
    count_logging_revisions,
    get_last_logging_revision,
    get_logging_revision_by_id,
    get_logging_revisions,
)
from src.nightcore.api.schemas.logging_revision import (
    ListLoggingRevisionMetaResponseSchema,
    LoggingRevisionDataSchema,
    LoggingRevisionMetaSchema,
)
from src.utils._enums import ConfigTypeEnum

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.infra.db.uow import UnitOfWork


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
        data: dict[str, Any],
        version: int,
    ):
        """
        Create a logging revision for a configuration change.

        Args:
            session: The async database session.
            guild_id: The ID of the guild where the change happened.
            user_id: The ID of the user who made the change.
            config_type: The type of the configuration that was changed.
            data: The updated configuration values.
            version: Version of ORM model.
        """

        revision_id = self.generate_revision_id()

        last_revision = await get_last_logging_revision(
            session, guild_id=guild_id, config_type=config_type
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
                data=data,
                version=version,
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
            created_at=revision.created_at,
        )

    async def list_revisions_by_params(
        self,
        *,
        guild: discord.Guild,
        config_types: "Sequence[ConfigTypeEnum] | None" = None,
        user_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ListLoggingRevisionMetaResponseSchema:
        """
        Get logging revisions for a guild.

        Args:
            guild: The guild to get the revisions for.
            config_types: Optional configuration types to filter by.
                ``None`` means no filtering by configuration type.
            user_id: Optional author id to filter revisions by.
            date_from: Optional inclusive lower bound on creation time.
            date_to: Optional inclusive upper bound on creation time.
            limit: The maximum number of revisions to return.
            offset: The number of revisions to skip.

        Returns:
            A page of LoggingRevisionSchema objects together with the total
            number of revisions matching the filters.
        """

        async with self._uow.start() as session:
            revisions = await get_logging_revisions(
                session,
                guild_id=guild.id,
                config_types=config_types,
                user_id=user_id,
                date_from=date_from,
                date_to=date_to,
                limit=limit,
                offset=offset,
            )

            total = await count_logging_revisions(
                session,
                guild_id=guild.id,
                config_types=config_types,
                user_id=user_id,
                date_from=date_from,
                date_to=date_to,
            )

        user_ids = [revision.user_id for revision in revisions]

        members: dict[int, discord.Member] = {}
        if user_ids:
            fetched = await guild.query_members(user_ids=user_ids, cache=True)
            members = {member.id: member for member in fetched}

        return ListLoggingRevisionMetaResponseSchema(
            total=total,
            revisions=[
                self._map_revision_to_schema(revision, members)
                for revision in revisions
            ],
        )

    async def get_by_params(
        self, *, guild_id: int, revision_id: str, config_type: ConfigTypeEnum
    ) -> LoggingRevisionDataSchema:
        """
        Get a specific logging revision for a guild.

        Stale revisions (older than the configuration model version) are
        migrated in place by patching their data and bumping the stored
        version, so the returned values always match the current schema.

        Args:
            guild_id: The ID of the guild the revision belongs to.
            revision_id: The revision ID to look up.
            config_type: The type of the configuration the revision
                belongs to.

        Raises:
            ValueError: If no configuration model is mapped for the
                config type, or the revision is newer than the
                configuration model version.

        Returns:
            A LoggingRevisionDataSchema containing the old and new data
            of the found revision (empty dicts when not found).
        """

        old_data: dict[str, Any] = {}
        new_data: dict[str, Any] = {}

        orm_model = CONFIG_MODEL_MAP.get(config_type)

        if orm_model is None:
            raise ValueError("Configuration model can't be `None`")

        async with self._uow.start() as session:
            current_revision = await get_logging_revision_by_id(
                session,
                guild_id=guild_id,
                revision_id=revision_id,
                config_type=config_type,
            )

            if current_revision is None:
                return LoggingRevisionDataSchema(
                    revision_id=revision_id,
                    old_data=old_data,
                    new_data=new_data,
                )

            down_revision = None
            if current_revision.down_revision_id:
                down_revision = await get_logging_revision_by_id(
                    session,
                    guild_id=guild_id,
                    revision_id=current_revision.down_revision_id,
                    config_type=config_type,
                )
                if down_revision is not None:
                    old_data = down_revision.data

            new_data = current_revision.data

            if current_revision.version < orm_model.__version__:  # type: ignore
                new_data = orm_model.patch_revision(new_data)  # type: ignore

                if old_data:
                    old_data = orm_model.patch_revision(old_data)  # type: ignore

                current_revision.data = new_data
                if down_revision is not None:
                    down_revision.data = old_data

            elif current_revision.version > orm_model.__version__:  # type: ignore
                raise ValueError(
                    "Revision version can't be greatest then ORM configuration model version."  # noqa: E501
                )

        return LoggingRevisionDataSchema(
            revision_id=revision_id,
            old_data=old_data,
            new_data=new_data,
        )
