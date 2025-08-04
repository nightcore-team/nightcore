"""This module defines base settings for environment variables loading using Pydantic."""  # noqa: E501

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ABS_PATH = Path(__file__).parent.parent.parent


class BaseEnvConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ABS_PATH / ".env.production",
        env_file_encoding="utf-8",
        extra="ignore",
    )
