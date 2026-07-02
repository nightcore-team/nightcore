from typing import Any

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base
from src.infra.db.models.discord_webhook import DiscordWebhook


class GuildForumConfig(IdIntegerMixin, Base):
    """Forum configuration for a guild."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    section_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, unique=True
    )
    _notify_webhook_id: Mapped[int | None] = mapped_column(
        "notify_webhook_id",
        ForeignKey("discordwebhook.id", ondelete="SET NULL"),
        nullable=True,
    )
    notify_webhook: Mapped[DiscordWebhook | None] = relationship(
        DiscordWebhook,
        foreign_keys=[_notify_webhook_id],
        lazy="selectin",
        cascade="all, delete-orphan",
        single_parent=True,
    )
    role_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, unique=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    prefix_id: Mapped[int | None] = mapped_column(
        Boolean, nullable=True, default=False
    )

    @property
    def available(self) -> bool:  # noqa: D102
        return self.section_id is not None

    @staticmethod
    def normalize_from_json(config: dict[str, Any]) -> dict[str, Any]:
        if "notify_webhook" in config:
            config["notify_webhook"] = DiscordWebhook(
                **config["notify_webhook"]
            )

        return config
