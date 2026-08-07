"""
Base classes for casino game state.

Used to describe the runtime state of a game that is persisted in the
``CasinoGame.state_data`` JSON column. Each game defines its own state
model inheriting from :class:`CasinoState`.
"""

from typing import Any, Self

from pydantic import BaseModel


class CasinoState(BaseModel):
    """Contract for game state stored in ``CasinoGame.state_data``."""

    @classmethod
    def load(cls, raw: dict[str, Any] | None) -> Self | None:
        """Deserialize raw database data into a state instance.

        Args:
            raw: Raw data from ``CasinoGame.state_data`` or ``None``.

        Returns:
            State instance or ``None`` when no data is stored.
        """
        if raw is None:
            return None
        return cls.model_validate(raw)

    def dump(self) -> dict[str, Any]:
        """Serialize state into a plain dict for the database."""
        return self.model_dump()
