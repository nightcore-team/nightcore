"""This module contains the dependencies for the API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import HTTPException, Request, status
from fastapi.params import Depends

from src.nightcore.api.security.jwt import JWTTokenService
from src.nightcore.api.services.access import AccessService
from src.nightcore.api.services.guild_state import GuildStateService

if TYPE_CHECKING:
    from src.infra.db.uow import UnitOfWork
    from src.nightcore.bot import Nightcore


def get_bot(request: Request) -> Nightcore:
    """Dependency to inject the Nightcore to the endpoint.."""

    return request.app.state.bot


def get_uow(request: Request) -> UnitOfWork:
    """Dependency to inject the UnitOfWork to the endpoint."""

    uow = getattr(
        request.app.state,
        "uow",
        None,
    )

    if uow is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="UnitOfWork is unavailable.",
        )

    return uow


def get_jwt_token_service(request: Request) -> JWTTokenService:
    """Dependency to inject the JWTTokenService to the endpoint."""

    return JWTTokenService(request.app.state.config.jwt)


def get_user_id(
    request: Request,
    jwt_token_service: Annotated[
        JWTTokenService,
        Depends(get_jwt_token_service),
    ],
) -> int:
    """Dependency to get the user ID from the request."""

    token = request.headers.get("Authorization")

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT token not found.",
        )

    payload = jwt_token_service.decode(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid JWT token.",
        )

    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bad token payload.",
        )

    try:
        return int(user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bad token payload.",
        ) from e


def get_access_service(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    bot: Annotated[Nightcore, Depends(get_bot)],
) -> AccessService:
    """Dependency to inject the AccessService to the endpoint."""

    return AccessService(
        uow=uow,
        bot=bot,
    )


def get_guild_state_service(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    bot: Annotated[Nightcore, Depends(get_bot)],
) -> GuildStateService:
    """Dependency to inject the GuildStateService to the endpoint."""

    return GuildStateService(uow=uow, bot=bot)


UserIdDependency = Annotated[int, Depends(get_user_id)]
BotDependency = Annotated[Nightcore, Depends(get_bot)]
GuildStateServiceDependency = Annotated[
    GuildStateService, Depends(get_guild_state_service)
]
AccessServiceDependency = Annotated[AccessService, Depends(get_access_service)]
