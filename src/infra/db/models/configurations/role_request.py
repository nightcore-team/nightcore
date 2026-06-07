from sqlalchemy import (
    BigInteger,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
    and_,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base
from src.utils._enums import OrganizationalRoleTypeEnum


class GuildOrganizationalRole(IdIntegerMixin, Base):
    __table_args__ = (
        UniqueConstraint("guild_id", "role_id", name="uq_org_guild_role"),
    )

    guild_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("guildrolerequestconfig.guild_id", ondelete="CASCADE"),
        nullable=False,
    )
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    tag: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[OrganizationalRoleTypeEnum] = mapped_column(
        Enum(
            OrganizationalRoleTypeEnum,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],  # type: ignore
            validate_strings=True,
        ),
        nullable=False,
    )


class GuildRoleRequestConfig(IdIntegerMixin, Base):
    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    illegal_roles: Mapped[list[GuildOrganizationalRole]] = relationship(
        GuildOrganizationalRole,
        lazy="selectin",
        cascade="all, delete-orphan",
        primaryjoin=lambda: and_(
            GuildRoleRequestConfig.guild_id
            == GuildOrganizationalRole.guild_id,
            GuildOrganizationalRole.type == OrganizationalRoleTypeEnum.ILLEGAL,
        ),
    )
    organizational_roles: Mapped[list[GuildOrganizationalRole]] = relationship(
        GuildOrganizationalRole,
        lazy="selectin",
        cascade="all, delete-orphan",
        primaryjoin=lambda: and_(
            GuildRoleRequestConfig.guild_id
            == GuildOrganizationalRole.guild_id,
            GuildOrganizationalRole.type == OrganizationalRoleTypeEnum.LEGAL,
        ),
    )
    check_role_requests_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
