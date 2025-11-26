"""Setup logging utilities for the application."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import colorlog

from src.utils.logging.config import (
    COLOR_FORMATTER,
    DEFAULT_LOGGING_LEVEL_DICT,
    FILE_FORMATTER,
)

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def _make_file_handler(name: str) -> RotatingFileHandler:
    file_path = LOG_DIR / f"{name}.log"
    handler = RotatingFileHandler(
        file_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    handler.setLevel(DEFAULT_LOGGING_LEVEL_DICT.get(name, logging.INFO))
    handler.setFormatter(FILE_FORMATTER)
    return handler


def setup_logging() -> tuple[logging.Logger, ...]:
    """Set up and configure logging for the entire application."""
    root_logger = logging.getLogger()
    root_logger.setLevel(DEFAULT_LOGGING_LEVEL_DICT.get("main", logging.INFO))

    # --- Console handler ---
    console_handler = colorlog.StreamHandler(sys.stdout)
    console_handler.setLevel(
        DEFAULT_LOGGING_LEVEL_DICT.get("main", logging.INFO)
    )
    console_handler.setFormatter(COLOR_FORMATTER)

    # --- File handlers ---
    general_file_handler = _make_file_handler("main")
    discord_file_handler = _make_file_handler("discord")
    sqlalchemy_file_handler = _make_file_handler("sqlalchemy")
    root_logger.handlers = [console_handler, general_file_handler]

    # --- Discord ---
    discord_logger = logging.getLogger("discord")
    discord_logger.handlers.clear()
    discord_logger.setLevel(
        DEFAULT_LOGGING_LEVEL_DICT.get("discord", logging.INFO)
    )
    discord_logger.addHandler(discord_file_handler)
    discord_logger.propagate = True

    # --- SQLAlchemy ---
    for name in ("sqlalchemy.engine", "sqlalchemy.pool"):
        sa_logger = logging.getLogger(name)
        sa_logger.handlers.clear()
        sa_logger.setLevel(DEFAULT_LOGGING_LEVEL_DICT.get(name, logging.INFO))
        sa_logger.addHandler(sqlalchemy_file_handler)
        sa_logger.propagate = True

    # --- asyncio та aiohttp ---
    for name in ("asyncio", "aiohttp.client"):
        sub_logger = logging.getLogger(name)
        sub_logger.setLevel(logging.INFO)
        sub_logger.propagate = True

    return (
        root_logger,
        discord_logger,
    )
