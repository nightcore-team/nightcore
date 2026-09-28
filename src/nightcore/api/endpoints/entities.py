"""Entity endpoints for guild-scoped entities."""

from fastapi import HTTPException, status
from fastapi.routing import APIRouter

from src.infra.db.operations import ENTITY_MODEL_MAP
from src.nightcore.api.dependencies import (
    AccessServiceDependency,
    BotDependency,
    EntityStateServiceDependency,
    UserIdDependency,
)
from src.nightcore.api.schemas.entities import (
    EntityBatchResult,
    EntityBatchUpdateBody,
)
from src.nightcore.utils import ensure_member_exists
from src.utils._enums import ConfigTypeEnum

router = APIRouter(prefix="/guilds", tags=["Guild Entities"])


@router.patch(
    "/{guild_id}/entities",
    status_code=status.HTTP_200_OK,
    response_model=EntityBatchResult,
)
async def update_entities(
    guild_id: int,
    body: EntityBatchUpdateBody,
    user_id: UserIdDependency,
    bot: BotDependency,
    access_service: AccessServiceDependency,
    entity_state_service: EntityStateServiceDependency,
) -> EntityBatchResult:
    """Batch update/create entities of a specific type for a guild."""

    guild = bot.get_guild(guild_id)

    if guild is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unknown guild"
        )

    member = await ensure_member_exists(guild, user_id)

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this guild",
        )

    # Check if entity type is valid
    if body.entity_type not in ENTITY_MODEL_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown entity type: {body.entity_type}",
        )

    # Check access
    has_access = await access_service.has_config_access(
        member=member, config_type=ConfigTypeEnum.ECONOMY
    )

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to manage entities",
        )

    return await entity_state_service.batch_update_entities(
        member=member,
        entity_type=body.entity_type,
        items=body.items,
    )
