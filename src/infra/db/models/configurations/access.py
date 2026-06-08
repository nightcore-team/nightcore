from sqlalchemy import (
    ARRAY,
    BigInteger,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class GuildAccessConfig(IdIntegerMixin, Base):
    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )

    # Access to GuildForumConfig
    forum_config_access_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )

    # Access to GuildOrgRolesConfig
    org_roles_config_access_roles_ids: Mapped[list[int] | None] = (
        mapped_column(ARRAY(BigInteger), nullable=True)
    )

    # Access to GuildProposalConfig
    proposal_config_access_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )

    # Access to GuildRulesConfig
    rules_config_access_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )

    # Access to GuildMultiplersConfig
    multiplers_config_access_roles_ids: Mapped[list[int] | None] = (
        mapped_column(ARRAY(BigInteger), nullable=True)
    )

    # Access to GuildLoggingConfig
    logging_config_access_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )

    # Access to GuildEconomyConfig
    economy_config_access_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )

    # Access to GuildLevelsConfig
    levels_config_access_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )

    # Access to GuildClansConfig
    clans_config_access_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )

    # Access to GuildPrivateChannelsConfig
    private_channels_config_access_roles_ids: Mapped[list[int] | None] = (
        mapped_column(ARRAY(BigInteger), nullable=True)
    )

    # Access to GuildModerationConfig
    moderation_config_access_roles_ids: Mapped[list[int] | None] = (
        mapped_column(ARRAY(BigInteger), nullable=True)
    )

    # Access to GuildNotificationsConfig
    notifications_config_access_roles_ids: Mapped[list[int] | None] = (
        mapped_column(ARRAY(BigInteger), nullable=True)
    )

    # Access to GuildTicketsConfig
    tickets_config_access_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )

    # Access to GuildInfomakerConfig
    infomaker_config_access_roles_ids: Mapped[list[int] | None] = (
        mapped_column(ARRAY(BigInteger), nullable=True)
    )
