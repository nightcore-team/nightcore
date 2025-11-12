"""Configuration constants for logging setup."""

from logging import INFO, Formatter
from typing import Final

import colorlog

DEFAULT_LOGGING_LEVEL_DICT: Final[dict[str, int]] = {
    "main": INFO,
    "discord": INFO,
    "sqlalchemy": INFO,
    "sqlalchemy.engine": INFO,
    "sqlalchemy.pool": INFO,
    "asyncio": INFO,
    "aiohttp": INFO,
    "aiohttp.client": INFO,
}

FILE_FORMATTER = Formatter(
    "%(asctime)s ~ %(name)-8s ~ %(levelname)-2s ~ %(message)s"
)


COLOR_FORMATTER = colorlog.ColoredFormatter(
    "%(log_color)s%(asctime)s ~ %(name)-8s ~ %(levelname)-2s ~ %(message_log_color)s%(message)s",  # noqa: E501
    log_colors={
        "DEBUG": "cyan",
        "INFO": "white",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold_red",
    },
    secondary_log_colors={
        "message": {
            "DEBUG": "cyan",
            "INFO": "light_purple",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        }
    },
)
