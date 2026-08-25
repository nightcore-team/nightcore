"""Database models for guild rules configuration."""

from typing import Any

from sqlalchemy import BigInteger, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base
from src.infra.db.models.discord_webhook import DiscordWebhook


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
    __table_args__ = (
        UniqueConstraint(
            "guild_id",
            name="uq_guild",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

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
    _rules_webhook_id: Mapped[int | None] = mapped_column(
        "rules_webhook_id",
        ForeignKey("discordwebhook.id", ondelete="SET NULL"),
        nullable=True,
    )
    rules_webhook: Mapped[DiscordWebhook | None] = relationship(
        DiscordWebhook,
        foreign_keys=[_rules_webhook_id],
        lazy="selectin",
        cascade="all, delete-orphan",
        single_parent=True,
    )

    @staticmethod
    def normalize_from_json(config: dict[str, Any]) -> dict[str, Any]:
        raw_rules = config.get("guild_rules")

        if raw_rules is not None:
            chapters: list[GuildRulesChapter] = []
            for chapter_data in raw_rules.get("chapters", []):
                rules: list[GuildRulesRule] = []
                for rule_data in chapter_data.get("rules", []):
                    subrules = [
                        GuildRulesSubRule(text=sr["text"])
                        for sr in rule_data.get("subrules", [])
                    ]
                    rules.append(
                        GuildRulesRule(
                            text=rule_data["text"], subrules=subrules
                        )
                    )
                chapters.append(
                    GuildRulesChapter(text=chapter_data["text"], rules=rules)
                )

            config["guild_rules"] = GuildRules(chapters=chapters)

        if "rules_webhook" in config:
            webhook = config["rules_webhook"]
            config["rules_webhook"] = (
                DiscordWebhook(**webhook) if webhook is not None else None
            )

        return config

    __version__ = 1

    @staticmethod
    def patch_revision(data: dict[str, Any]) -> dict[str, Any]:
        """Apply a patch to a config revision data dict."""
        ...
