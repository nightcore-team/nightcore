"""Available-guilds related endpoints."""

from fastapi import status
from fastapi.routing import APIRouter

from src.nightcore.api.dependencies import (
    AccessServiceDependency,
    UserIdDependency,
)
from src.nightcore.api.schemas.guild import GuildInfoSchema

router = APIRouter(prefix="/available-guilds")


@router.get(
    "",
    response_model=list[GuildInfoSchema],
    status_code=status.HTTP_200_OK,
)
def get_available_guilds(
    user_id: UserIdDependency, access_service: AccessServiceDependency
):
    """Get the guilds a user is in that the bot is also in."""

    return access_service.get_user_guilds(user_id)
