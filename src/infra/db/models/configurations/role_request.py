from typing import Any

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

    @staticmethod
    def normalize_from_json(config: dict[str, Any]) -> dict[str, Any]:
        if "organizational_roles" in config:
            org_roles: list[Any] = config["organizational_roles"] or []
            config["organizational_roles"] = [
                GuildOrganizationalRole(
                    **item, type=OrganizationalRoleTypeEnum.LEGAL
                )
                for item in org_roles
            ]

        if "illegal_roles" in config:
            illegal_roles: list[Any] = config["illegal_roles"] or []
            config["illegal_roles"] = [
                GuildOrganizationalRole(
                    **item, type=OrganizationalRoleTypeEnum.ILLEGAL
                )
                for item in illegal_roles
            ]

        return config

    __version__ = 1

    @staticmethod
    def patch_revision(data: dict[str, Any]) -> dict[str, Any]:
        """Apply a patch to a config revision data dict."""
        ...
