"""Entity state service implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import discord
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase

from src.infra.db.operations import (
    ENTITY_MODEL_MAP,
    get_entities_by_type,
    get_specified_entities,
)
from src.infra.db.uow import UnitOfWork
from src.nightcore.api.schemas.entities import (
    ENTITY_SCHEMA_MODEL_MAP,
    EntityBaseSchema,
    EntityBatchError,
    EntityBatchItem,
    EntityBatchResult,
)
from src.nightcore.api.utils.validators import (
    ValidationContext,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.utils._enums import EntityTypeEnum


class EntityStateService:
    def __init__(
        self,
        uow: UnitOfWork,
        bot: Nightcore,
    ) -> None:
        self._bot = bot
        self._uow = uow

    async def _build_validation_context(
        self, member: discord.Member
    ) -> ValidationContext:
        return ValidationContext(bot=self._bot, interaction_member=member)

    async def batch_update_entities(
        self,
        member: discord.Member,
        entity_type: EntityTypeEnum,
        items: list[EntityBatchItem],
    ) -> EntityBatchResult:
        """Batch update/create/delete entities of a specific type."""

        model = ENTITY_MODEL_MAP.get(entity_type)
        if model is None:
            raise ValueError(f"Unknown entity type: {entity_type}")

        schema = ENTITY_SCHEMA_MODEL_MAP.get(entity_type)
        if schema is None:
            raise ValueError(
                f"Schema not found for entity type: {entity_type}"
            )

        # 1. Split the batch: deletes carry no payload, so they skip schema
        #    validation entirely; everything else is validated before the
        #    transaction is opened.
        delete_items = [
            (idx, item) for idx, item in enumerate(items) if item.delete
        ]
        upsert_items = [
            (idx, item) for idx, item in enumerate(items) if not item.delete
        ]

        validated_items: list[tuple[int, EntityBatchItem, Any]] = []
        errors: list[EntityBatchError] = []

        context = await self._build_validation_context(member=member)

        for idx, item in upsert_items:
            try:
                validated = schema.model_validate(
                    item.data, extra="ignore", context=context
                )
                validated_items.append((idx, item, validated))
            except Exception as e:
                errors.append(
                    EntityBatchError(
                        index=idx,
                        entity_id=item.entity_id,
                        error=str(e),
                    )
                )

        if not validated_items and not delete_items:
            return EntityBatchResult(updated=[], errors=errors)

        # Split create/update
        update_items = [
            (idx, item, v)
            for idx, item, v in validated_items
            if item.entity_id > 0
        ]

        update_ids = [item.entity_id for _, item, _ in update_items]
        delete_ids = [item.entity_id for _, item in delete_items]

        # 2. Single transaction
        async with self._uow.start() as session:
            # Load existing entities for update and delete (FOR UPDATE)
            # using a single batch operation
            existing: dict[int, Any] = {}
            lookup_ids = update_ids + delete_ids
            if lookup_ids:
                entities = await get_specified_entities(
                    session,
                    entity_type=entity_type,
                    guild_id=member.guild.id,
                    entity_ids=lookup_ids,
                    for_update=True,
                )
                for entity in entities:
                    existing[entity.id] = entity

            updated_entities: list[dict[str, Any]] = []

            # Check missing update_ids
            for idx, item, _ in update_items:
                if item.entity_id not in existing:
                    errors.append(
                        EntityBatchError(
                            index=idx,
                            entity_id=item.entity_id,
                            error="Сущность не найдена",
                        )
                    )

            # Deletions carry a real entity_id, so they resolve against the
            # same loaded set as updates.
            for idx, item in delete_items:
                entity = existing.get(item.entity_id)
                if entity is None:
                    errors.append(
                        EntityBatchError(
                            index=idx,
                            entity_id=item.entity_id,
                            error="Сущность не найдена",
                        )
                    )
                    continue

                try:
                    async with session.begin_nested():
                        await session.delete(entity)
                        await session.flush()
                except IntegrityError as e:
                    errors.append(
                        EntityBatchError(
                            index=idx,
                            entity_id=item.entity_id,
                            error=self._describe_conflict(e),
                        )
                    )
                    # Drop the row from the session, otherwise every later
                    # flush retries the very delete that just failed.
                    session.expunge(entity)

            # Process all validated items
            for idx, item, validated in validated_items:
                if item.entity_id > 0 and item.entity_id not in existing:
                    continue  # Already added to errors

                try:
                    async with session.begin_nested():
                        dump = validated.model_dump(
                            exclude_unset=True,
                            exclude_computed_fields=True,
                            # Response-only fields: a client must never be
                            # able to reassign the primary key or the owner
                            # guild.
                            exclude={"id", "guild_id"},
                        )
                        normalized = model.normalize_from_json(dump)

                        if item.entity_id > 0:
                            # UPDATE
                            entity = existing[item.entity_id]
                        else:
                            # CREATE
                            entity = model(
                                guild_id=member.guild.id, **normalized
                            )
                            session.add(entity)

                        # Apply normalized fields
                        for k, v in normalized.items():
                            setattr(entity, k, v)

                        await session.flush()
                except IntegrityError as e:
                    errors.append(
                        EntityBatchError(
                            index=idx,
                            entity_id=item.entity_id,
                            error=self._describe_conflict(e),
                        )
                    )

                    if item.entity_id > 0:
                        # Rolling a savepoint back leaves mutated attributes
                        # in memory, so reload the row before it is touched
                        # by a later flush.
                        await session.refresh(existing[item.entity_id])
                    continue

                new_data = self._serialize_entity(schema, entity)

                updated_entities.append(new_data)

        return EntityBatchResult(updated=updated_entities, errors=errors)

    @staticmethod
    def _describe_conflict(error: IntegrityError) -> str:
        """Turn a database constraint violation into a readable message."""

        return "Нарушено уникальное ограничение в базе данных"

    def _serialize_entity(
        self, schema: type[EntityBaseSchema], entity: DeclarativeBase
    ) -> dict[str, Any]:
        """Serialize entity using its Pydantic schema."""

        return schema.model_construct(**vars(entity)).model_dump(mode="json")

    async def get_entities(
        self,
        member: discord.Member,
        entity_type: EntityTypeEnum,
    ) -> list[dict[str, Any]]:
        """Get all entities of a specific type for a guild."""

        model = ENTITY_MODEL_MAP.get(entity_type)
        if model is None:
            raise ValueError(f"Unknown entity type: {entity_type}")

        schema = ENTITY_SCHEMA_MODEL_MAP.get(entity_type)
        if schema is None:
            raise ValueError(
                f"Schema not found for entity type: {entity_type}"
            )

        async with self._uow.start() as session:
            entities = await get_entities_by_type(
                session,
                entity_type=entity_type,
                guild_id=member.guild.id,
            )

        return [self._serialize_entity(schema, e) for e in entities]
