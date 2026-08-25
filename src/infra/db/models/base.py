"""Base model for SQLAlchemy ORM with async support."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(AsyncAttrs, DeclarativeBase):
    @declared_attr.directive
    def __tablename__(self) -> str:  # noqa: D105
        return f"{self.__name__.lower()}"

    @staticmethod
    def normalize_from_json(config: dict[str, Any]) -> dict[str, Any]:
        return config
