from sqlalchemy import (
    ARRAY,
    BigInteger,
    Enum,
    Float,
    ForeignKey,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base
from src.utils._enums import ConfigMuteTypeEnum


class GuildFractionRole(IdIntegerMixin, Base):
    __table_args__ = (
        UniqueConstraint(
            "guild_id",
            "role_id",
            name="uq_fraction_guild_role",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    guild_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("guildmoderationconfig.guild_id", ondelete="CASCADE"),
        nullable=False,
    )
    role_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    access_roles: Mapped[list[int]] = mapped_column(
        ARRAY(BigInteger), nullable=False
    )


class GuildModerationConfig(IdIntegerMixin, Base):  #
    """Moderation configuration for a guild."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    moderation_access_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )  #
    leadership_access_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )  #
    leader_access_rr_roles_ids: Mapped[list[int]] = mapped_column(
        ARRAY(BigInteger), nullable=False, default=list
    )  #
    count_moderator_messages_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )  #
    ban_access_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )  #
    unban_access_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    mute_score: Mapped[float | None] = mapped_column(
        Float, nullable=False, default=0.0, server_default=text("0.0")
    )  #
    ban_score: Mapped[float | None] = mapped_column(
        Float, nullable=False, default=0.0, server_default=text("0.0")
    )  #
    kick_score: Mapped[float | None] = mapped_column(
        Float, nullable=False, default=0.0, server_default=text("0.0")
    )  #
    ticket_score: Mapped[float | None] = mapped_column(
        Float, nullable=False, default=0.0, server_default=text("0.0")
    )  #
    role_request_score: Mapped[float | None] = mapped_column(
        Float, nullable=False, default=0.0, server_default=text("0.0")
    )
    role_remove_score: Mapped[float | None] = mapped_column(
        Float, nullable=False, default=0.0, server_default=text("0.0")
    )
    ticket_ban_score: Mapped[float | None] = mapped_column(
        Float, nullable=False, default=0.0, server_default=text("0.0")
    )
    mpmute_score: Mapped[float | None] = mapped_column(
        Float, nullable=False, default=0.0, server_default=text("0.0")
    )
    vmute_score: Mapped[float | None] = mapped_column(
        Float, nullable=False, default=0.0, server_default=text("0.0")
    )
    message_score: Mapped[float | None] = mapped_column(
        Float, nullable=False, default=0.0, server_default=text("0.0")
    )
    notification_score: Mapped[float | None] = mapped_column(
        Float, nullable=False, default=0.0, server_default=text("0.0")
    )

    trackable_moderation_role_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )  #

    ban_request_ping_role_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )  #
    send_ban_request_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )  #
    mpmute_role_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )  #
    vmute_role_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )  ##
    mute_role_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    mute_type: Mapped[ConfigMuteTypeEnum | None] = mapped_column(
        Enum(
            ConfigMuteTypeEnum,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],  # type: ignore
            validate_strings=True,
        ),
        nullable=True,
        default=ConfigMuteTypeEnum.TIMEOUT,
    )  #
    fraction_roles_access_roles_ids: Mapped[list[GuildFractionRole]] = (
        relationship(
            GuildFractionRole,
            lazy="selectin",
            cascade="all, delete-orphan",
        )
    )
