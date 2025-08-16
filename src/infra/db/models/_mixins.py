"""This file contains mixins for database models."""

from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.now
    )


class IdIntegerMixin:
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
