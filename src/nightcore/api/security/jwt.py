"""JWT token verification utilities."""

from typing import Any

from jose import JWTError, jwt

from .config import Config as JWTConfig

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


class JWTTokenService:
    def __init__(self, config: JWTConfig) -> None:
        self.config = config
        if self.config.JWT_ALGORITHM not in ALLOWED_JWT_ALGORITHMS:
            msg = (
                f"JWT_ALGORITHM '{self.config.JWT_ALGORITHM}' "
                f"not in allowlist {sorted(ALLOWED_JWT_ALGORITHMS)}"
            )
            raise ValueError(msg)

    @staticmethod
    def _strip_bearer(token: str) -> str:
        """Strip Bearer prefix if present (case-insensitive)."""
        stripped = token.strip()
        if stripped[:7].lower() == "bearer ":
            return stripped[7:].strip()
        return stripped

    def decode(self, token: str) -> dict[str, Any] | None:
        """Verify a JWT token and return its payload if valid, otherwise None."""  # noqa: E501

        # Bearer prefix stripping
        token = self._strip_bearer(token)

        # Allowlist enforcement at decode time as defense-in-depth
        if self.config.JWT_ALGORITHM not in ALLOWED_JWT_ALGORITHMS:
            return None

        try:
            res = jwt.decode(
                token,
                self.config.JWT_PUBLIC,
                algorithms=[self.config.JWT_ALGORITHM],
                options={
                    "require_exp": True,
                    "require_aud": True,
                    "require_iss": True,
                },
            )
            # Extra defense for claims
            if not res.get("exp") or not res.get("aud") or not res.get("iss"):
                return None
            return res
        except JWTError:
            return None
