from sqlalchemy import BigInteger, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class GuildOrganizationalRole(IdIntegerMixin, Base):
    __table_args__ = (
        UniqueConstraint(
            "guild_id", "role_id", "tag", "name", name="uq_guild_role_name_tag"
        ),
    )

    guild_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("guildrolerequestconfig.guild_id", ondelete="CASCADE"),
        nullable=False,
    )
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    tag: Mapped[str] = mapped_column(String, nullable=False)


class GuildRoleRequestConfig(IdIntegerMixin, Base):
    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    illegal_roles: Mapped[list[GuildOrganizationalRole]] = relationship(
        GuildOrganizationalRole,
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    organizational_roles: Mapped[list[GuildOrganizationalRole]] = relationship(
        GuildOrganizationalRole,
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    check_role_requests_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
