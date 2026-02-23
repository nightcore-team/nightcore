"""Processed forum thread model for the Nightcore bot database."""

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models.base import Base


class ProcessedForumThread(Base):
    thread_id: Mapped[int] = mapped_column(
        Integer, nullable=False, unique=True, primary_key=True
    )
