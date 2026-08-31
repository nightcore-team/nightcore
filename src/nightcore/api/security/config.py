"""Defines the Config class for Jwt environment settings."""

import base64
import binascii

from pydantic import field_validator

from src.config.env import BaseEnvConfig

ALLOWED_JWT_ALGORITHMS = frozenset(
    {
        "RS256",
        "RS384",
        "RS512",
        "ES256",
        "ES384",
        "ES512",
    }
)


class Config(BaseEnvConfig):
    JWT_PUBLIC: str
    JWT_ALGORITHM: str

    @field_validator("JWT_PUBLIC", mode="before")
    @classmethod
    def decode_public_key(cls, v: str) -> str:
        """Decode the base64-encoded public key."""

        if not isinstance(v, str):
            raise ValueError("JWT_PUBLIC must be a base64-encoded string")
        try:
            # validate=True ensures correct padding and charset
            return base64.b64decode(v, validate=True).decode("utf-8")
        except (binascii.Error, ValueError, UnicodeDecodeError) as exc:
            raise ValueError(f"Invalid base64 JWT_PUBLIC: {exc}") from exc

    @field_validator("JWT_ALGORITHM")
    @classmethod
    def validate_algorithm(cls, v: str) -> str:
        """Allowlist JWT_ALGORITHM."""

        if v not in ALLOWED_JWT_ALGORITHMS:
            raise ValueError(
                f"JWT_ALGORITHM '{v}' not in allowlist {sorted(ALLOWED_JWT_ALGORITHMS)}"  # noqa: E501
            )
        return v
