"""Database models for guild rules configuration."""

from sqlalchemy import BigInteger, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class GuildRulesSubRule(IdIntegerMixin, Base):
    rule_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("guildrulesrule.id", ondelete="CASCADE"),
        nullable=False,
    )
    text: Mapped[str] = mapped_column(String, nullable=False)


class GuildRulesRule(IdIntegerMixin, Base):
    chapter_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("guildruleschapter.id", ondelete="CASCADE"),
        nullable=False,
    )
    subrules: Mapped[list[GuildRulesSubRule]] = relationship(
        GuildRulesSubRule,
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    text: Mapped[str] = mapped_column(String, nullable=False)


class GuildRulesChapter(IdIntegerMixin, Base):
    rules_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("guildrules.id", ondelete="CASCADE"),
        nullable=False,
    )
    rules: Mapped[list[GuildRulesRule]] = relationship(
        GuildRulesRule,
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    text: Mapped[str] = mapped_column(String, nullable=False)


class GuildRules(IdIntegerMixin, Base):
    __table_args__ = (UniqueConstraint("guild_id", name="uq_guild"),)

    guild_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("guildrulesconfig.guild_id", ondelete="CASCADE"),
        nullable=False,
    )
    chapters: Mapped[list[GuildRulesChapter]] = relationship(
        GuildRulesChapter,
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class GuildRulesConfig(IdIntegerMixin, Base):
    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    guild_rules: Mapped[GuildRules | None] = relationship(
        GuildRules,
        lazy="selectin",
        cascade="all, delete-orphan",
        uselist=False,
        passive_deletes=True,
    )
    rules_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
