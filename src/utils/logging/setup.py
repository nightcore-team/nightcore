"""Setup logging utilities for the application."""

import logging
import sys
from logging import Handler
from logging.handlers import QueueHandler, QueueListener
from queue import Queue

from src.utils.logging.config import (
    # COLOR_FORMATTER,
    DEFAULT_LOGGING_LEVEL_DICT,
    FILE_FORMATTER,
)

_queue = Queue()  # pyright: ignore[reportUnknownVariableType]
_listener: QueueListener | None = None


def setup_logging() -> logging.Logger:
    """Set up and configure logging for the entire application."""
    handlers: list[Handler] = []

    root_logger = logging.getLogger()
    root_logger.setLevel(DEFAULT_LOGGING_LEVEL_DICT.get("main", logging.INFO))

    # --- Console handler ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(
        DEFAULT_LOGGING_LEVEL_DICT.get("main", logging.INFO)
    )
    # # console_handler.setFormatter(COLOR_FORMATTER)
    console_handler.setFormatter(FILE_FORMATTER)
    root_logger.addHandler(console_handler)

    handlers.append(console_handler)

    # --- Discord ---
    discord_logger = logging.getLogger("discord")
    discord_logger.setLevel(
        DEFAULT_LOGGING_LEVEL_DICT.get("discord", logging.INFO)
    )
    discord_logger.propagate = True

    # --- SQLAlchemy ---
    # for name in ("sqlalchemy.engine", "sqlalchemy.pool"):
    #     sa_logger = logging.getLogger(name)
    #     sa_logger.handlers.clear()
    #     sa_logger.setLevel(DEFAULT_LOGGING_LEVEL_DICT.get(name, logging.INFO))  # noqa: E501
    #     sa_logger.propagate = True

    # --- asyncio та aiohttp ---
    for name in ("asyncio", "aiohttp.client"):
        sub_logger = logging.getLogger(name)
        sub_logger.setLevel(logging.INFO)
        sub_logger.propagate = True

    # --- Queue handler ---
    queue_handler = QueueHandler(queue=_queue)  # pyright: ignore[reportUnknownArgumentType]
    queue_handler.setLevel(
        DEFAULT_LOGGING_LEVEL_DICT.get("main", logging.INFO)
    )

    root_logger.addHandler(queue_handler)

    _listener = QueueListener(
        _queue,  # pyright: ignore[reportUnknownArgumentType]
        *handlers,
        respect_handler_level=True,
    )
    _listener.start()

    return root_logger


def stop_logging():
    """Stop the logging QueueListener and flush pending records."""

    _listener.stop() if _listener else None
