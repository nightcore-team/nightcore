"""Defines the Config class for Jwt environment settings."""

import base64

from pydantic import field_validator

from src.config.env import BaseEnvConfig


class Config(BaseEnvConfig):
    JWT_PUBLIC: str
    JWT_ALGORITHM: str

    @field_validator("JWT_PUBLIC", mode="before")
    @classmethod
    def decode_public_key(cls, v: str) -> str:
        """Decode the base64-encoded public key."""

        return base64.b64decode(v).decode()
