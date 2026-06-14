from typing import Annotated

from fastapi import HTTPException, Request, status
from fastapi.params import Depends

from src.infra.db.uow import UnitOfWork
from src.nightcore.api.security.jwt import JWTTokenService
from src.nightcore.api.services.access import AccessService
from src.nightcore.api.services.guild_state import GuildStateService
from src.nightcore.bot import Nightcore


def get_bot(request: Request) -> Nightcore:
    return request.app.state.bot


async def get_uow(request: Request) -> UnitOfWork:
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
    return JWTTokenService(request.app.state.config.jwt)


def get_user_id(
    request: Request,
    jwt_token_service: Annotated[
        JWTTokenService,
        Depends(get_jwt_token_service),
    ],
) -> int:
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
    return AccessService(
        uow=uow,
        bot=bot,
    )


def get_guild_state_service(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    bot: Annotated[Nightcore, Depends(get_bot)],
) -> GuildStateService:
    return GuildStateService(uow=uow, bot=bot)


UserIdDependency = Annotated[int, Depends(get_user_id)]
BotDependency = Annotated[Nightcore, Depends(get_bot)]
GuildStateServiceDependency = Annotated[
    GuildStateService, Depends(get_guild_state_service)
]
AccessServiceDependency = Annotated[AccessService, Depends(get_access_service)]
