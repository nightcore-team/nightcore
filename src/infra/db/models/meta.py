"""Meta configuration model for guild config access management."""

from sqlalchemy import ARRAY, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class GuildMetaConfig(IdIntegerMixin, Base):
    """Meta configuration for guild configs access roles."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )

    # Access to MainGuildConfig
    other_config_access_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
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
    # tickets_config_access_roles_ids: Mapped[list[int] | None] = mapped_column(  # noqa: E501
    #     ARRAY(BigInteger), nullable=True
    # )

    # Access to GuildInfomakerConfig
    infomaker_config_access_roles_ids: Mapped[list[int] | None] = (
        mapped_column(ARRAY(BigInteger), nullable=True)
    )
