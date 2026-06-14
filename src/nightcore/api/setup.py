"""Setup module for creating and configuring the FastAPI bot instance."""

from typing import cast

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ExceptionHandler

from src.config.config import config
from src.nightcore.api.endpoints import router as api_router
from src.nightcore.api.events.exceptions import EXCEPTION_HANDLERS
from src.nightcore.bot import Nightcore


def create_fastapi(bot: Nightcore) -> FastAPI:
    """Create and return an instance of the FastAPI application."""

    app = FastAPI(title="Nightcore API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            config.api.DASHBOARD_FRONTEND_URI,
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["*"],
    )

    for exc_type, handler in EXCEPTION_HANDLERS.items():
        app.add_exception_handler(exc_type, cast(ExceptionHandler, handler))

    app.state.config = config
    app.state.bot = bot
    app.state.uow = bot.uow

    app.include_router(api_router)

    return app


def create_api_server(bot: Nightcore) -> uvicorn.Server:
    """Create the uvicorn server for the FastAPI application."""

    app = create_fastapi(bot)

    return uvicorn.Server(
        uvicorn.Config(
            app=app,
            host=config.api.API_HOST,
            port=config.api.API_PORT,
        )
    )


async def run_fastapi(server: uvicorn.Server) -> None:
    """Run the FastAPI application in the current event loop."""

    await server.serve()


def stop_fastapi(server: uvicorn.Server) -> None:
    """Gracefully stop the FastAPI server."""

    server.should_exit = True
