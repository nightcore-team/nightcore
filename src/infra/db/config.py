"""Defines the Config class for database environment settings."""

from pydantic import AliasChoices, Field, PostgresDsn, field_validator
from pydantic_core.core_schema import FieldValidationInfo
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from src.config.env import BaseEnvConfig


class Config(BaseEnvConfig):
    POSTGRES_USER: str | None = Field(
        default=None, validation_alias=AliasChoices("POSTGRES_USER", "PGUSER")
    )
    POSTGRES_PASSWORD: str | None = Field(
        default=None,
        validation_alias=AliasChoices("POSTGRES_PASSWORD", "PGPASSWORD"),
    )
    POSTGRES_HOST: str | None = Field(
        default=None, validation_alias=AliasChoices("POSTGRES_HOST", "PGHOST")
    )
    POSTGRES_PORT: int | None = Field(
        default=None, validation_alias=AliasChoices("POSTGRES_PORT", "PGPORT")
    )
    POSTGRES_DB: str | None = Field(
        default=None,
        validation_alias=AliasChoices("POSTGRES_DB", "PGDATABASE"),
    )

    POSTGRES_DATABASE_URI: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "POSTGRES_DATABASE_URI",
            "DATABASE_URL",
            "RAILWAY_DATABASE_URL",
            "POSTGRES_URL",
        ),
    )
    POSTGRES_ECHO: bool = False
    POSTGRES_ECHO_POOL: bool = True
    POSTGRES_POOL_MAX_OVERFLOW: int = 30
    POSTGRES_POOL_SIZE: int = 10
    POSTGRES_POOL_TIMEOUT: int = 0
    POSTGRES_POOL_PRE_PING: bool = True

    ENGINE: AsyncEngine | None = None

    @field_validator("POSTGRES_DATABASE_URI", mode="before")
    @classmethod
    def _assemble_db_connection(
        cls, v: str | None, info: FieldValidationInfo
    ) -> str:
        if isinstance(v, str):
            return v
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=info.data.get("POSTGRES_USER"),
                password=info.data.get("POSTGRES_PASSWORD"),
                host=info.data.get("POSTGRES_HOST"),
                port=info.data.get("POSTGRES_PORT"),
                path=f"{info.data.get('POSTGRES_DB') or ''}",
            )
        )

    @field_validator("ENGINE", mode="before")
    @classmethod
    def _assemble_db_engine(
        cls, v: AsyncEngine | None, info: FieldValidationInfo
    ) -> AsyncEngine:
        if isinstance(v, AsyncEngine):
            return v
        return create_async_engine(
            url=info.data.get("POSTGRES_DATABASE_URI"),  # type: ignore
            echo=info.data.get("POSTGRES_ECHO"),
            echo_pool=info.data.get("POSTGRES_ECHO_POOL"),
            max_overflow=info.data.get("POSTGRES_POOL_MAX_OVERFLOW"),
            pool_size=info.data.get("POSTGRES_POOL_SIZE"),
            pool_timeout=info.data.get("POSTGRES_POOL_TIMEOUT"),
            pool_pre_ping=info.data.get("POSTGRES_POOL_PRE_PING"),
        )
