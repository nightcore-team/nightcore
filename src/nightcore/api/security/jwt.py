"""JWT token verification utilities."""

from typing import Any

from jose import JWTError, jwt

from .config import Config as JWTConfig


class JWTTokenService:
    def __init__(self, config: JWTConfig) -> None:
        self.config = config

    def decode(self, token: str) -> dict[str, Any] | None:
        """Verify a JWT token and return its payload if valid, otherwise None."""  # noqa: E501

        try:
            res = jwt.decode(
                token, self.config.JWT_PUBLIC, self.config.JWT_ALGORITHM
            )
            return res
        except JWTError:
            return None
