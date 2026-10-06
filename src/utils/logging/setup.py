"""Setup logging utilities for the application."""

import logging
import sys
from logging import Handler
from logging.handlers import QueueHandler, QueueListener
from queue import Queue

from src.utils.logging.config import (
    DEFAULT_LOGGING_LEVEL_DICT,
    FILE_FORMATTER,
)

_queue: "Queue[logging.LogRecord]" = Queue()
_listener: QueueListener | None = None
_queue_handler: QueueHandler | None = None
_handlers: list[Handler] = []


def setup_logging() -> logging.Logger:
    """Set up and configure logging for the entire application."""
    global _listener, _queue_handler

    root_logger = logging.getLogger()

    if _listener is not None:
        return root_logger

    level = DEFAULT_LOGGING_LEVEL_DICT.get("main", logging.INFO)
    root_logger.setLevel(level)

    # --- Console handler ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(FILE_FORMATTER)
    _handlers.append(console_handler)

    # --- Discord ---
    discord_logger = logging.getLogger("discord")
    discord_logger.setLevel(
        DEFAULT_LOGGING_LEVEL_DICT.get("discord", logging.INFO)
    )
    discord_logger.propagate = True

    # --- asyncio та aiohttp ---
    for name in ("asyncio", "aiohttp.client"):
        sub_logger = logging.getLogger(name)
        sub_logger.setLevel(logging.INFO)
        sub_logger.propagate = True

    # --- Queue handler ---
    _queue_handler = QueueHandler(_queue)
    _queue_handler.setLevel(level)
    root_logger.addHandler(_queue_handler)

    _listener = QueueListener(_queue, *_handlers, respect_handler_level=True)
    _listener.start()

    return root_logger


def stop_logging() -> None:
    """Stop the listener, drain the queue and flush handlers."""

    global _listener, _queue_handler

    if _listener is None:
        return

    root_logger = logging.getLogger()

    _listener.stop()
    _listener = None

    if _queue_handler is not None:
        root_logger.removeHandler(_queue_handler)
        _queue_handler = None

    for handler in _handlers:
        root_logger.addHandler(handler)

    for handler in _handlers:
        handler.flush()

    logging.shutdown()
