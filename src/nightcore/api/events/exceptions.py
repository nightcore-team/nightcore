"""Exceptions handlers for the API."""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from src.nightcore.api.domain.exceptions.base import (
    ConfigValidationError,
    LogicalError,
)


async def unexpected_exception_handler(
    _: Request, exc: Exception
) -> JSONResponse:
    """Handle unexpected errors."""

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=""
    )


async def logical_error_handler(_: Request, exc: LogicalError) -> JSONResponse:

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=str(exc)
    )


async def config_validation_error(
    _: Request, exc: LogicalError
) -> JSONResponse:

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST, content=str(exc)
    )


EXCEPTION_HANDLERS = {
    Exception: unexpected_exception_handler,
    LogicalError: logical_error_handler,
    ConfigValidationError: config_validation_error,
}
