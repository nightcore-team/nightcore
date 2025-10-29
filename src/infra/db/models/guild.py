"""Guild model for the Nightcore bot database."""

from sqlalchemy import ARRAY, JSON, BigInteger, Float, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._annot import CoinDropAnnot, ColorDropAnnot, Rules
from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class MainGuildConfig(IdIntegerMixin, Base):  #
    """Main configuration for a guild."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    rules_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )  #
    create_proposal_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )  #
    proposals_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    organizational_roles: Mapped[dict[str, dict[str, int]]] = mapped_column(
        JSON, nullable=False, default=dict
    )  #
    fraction_roles: Mapped[list[int]] = mapped_column(
        ARRAY(BigInteger), nullable=False, default=list
    )  #
    voice_temp_roles: Mapped[dict[int, int]] = mapped_column(
        JSON, nullable=False, default=dict
    )  #
    faq: Mapped[dict[str, str]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    check_role_requests_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )  #
    guild_rules: Mapped["Rules"] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: {"chapters": []},  # type: ignore
    )  #


class GuildLoggingConfig(IdIntegerMixin, Base):  #
    """Logging configuration for a guild."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    bans_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    clans_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    members_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    messages_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    voices_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    moderation_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    tickets_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    roles_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    channels_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    reactions_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    private_rooms_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    economy_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    message_log_ignoring_channels_ids: Mapped[list[int] | None] = (
        mapped_column(ARRAY(BigInteger), nullable=True)
    )


class GuildEconomyConfig(IdIntegerMixin, Base):  #
    """Economy configuration for a guild."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )

    coin_name: Mapped[str | None] = mapped_column(String, nullable=True)
    economy_access_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    reward_bonus: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    economy_shop_buy_ping_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    economy_shop_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    economy_shop_items: Mapped[dict[str, float]] = mapped_column(
        JSON, nullable=False, default=dict, server_default=text("'{}'::json")
    )
    colors: Mapped[dict[str, str]] = mapped_column(
        JSON, nullable=False, default=dict, server_default=text("'{}'::json")
    )
    drop_from_coins_case: Mapped[list[CoinDropAnnot]] = mapped_column(
        JSON, nullable=False, default=dict, server_default=text("'{}'::json")
    )
    drop_from_colors_case: Mapped[list[ColorDropAnnot]] = mapped_column(
        JSON, nullable=False, default=dict, server_default=text("'{}'::json")
    )


class GuildLevelsConfig(IdIntegerMixin, Base):  #
    """Level configuration for a guild."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )

    count_messages_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    level_notify_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    base_exp_multiplier: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    temp_exp_multiplier: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    base_coins_multiplier: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    temp_coins_multiplier: Mapped[int | None] = mapped_column(
        Float, nullable=True
    )
    bonus_access_roles_ids: Mapped[dict[int, int]] = mapped_column(
        JSON, nullable=False, default=dict, server_default=text("'{}'::json")
    )
    level_roles: Mapped[dict[str, int]] = mapped_column(
        JSON, nullable=False, default=dict, server_default=text("'{}'::json")
    )
    count_messages_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="channel_only",
        server_default=text("'channel_only'"),
    )  # all | channel_only


class GuildClansConfig(IdIntegerMixin, Base):  # ---
    """Clans configuration for a guild."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    clan_payday_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    clan_shop_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    clan_shop_items: Mapped[dict[str, float]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    clans_access_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    create_clan_role_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    clan_buy_ping_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    clan_reputation_per_payday: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    base_exp_multiplier: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    clan_improvements: Mapped[list[int]] = mapped_column(
        ARRAY(Integer), nullable=False, default=list
    )


class GuildPrivateChannelsConfig(IdIntegerMixin, Base):  #
    """Private channels configuration for a guild."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    private_rooms_create_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
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
    count_moderator_messages_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )  #
    ban_access_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )  #
    mute_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ban_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    kick_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ticket_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    role_request_score: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    role_remove_score: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    ticket_ban_score: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    mpmute_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    vmute_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    message_score: Mapped[float | None] = mapped_column(Float, nullable=True)

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
    mute_type: Mapped[str] = mapped_column(
        String, nullable=False, default="role"
    )  #
    fraction_roles_access_roles_ids: Mapped[list[int]] = mapped_column(
        ARRAY(BigInteger), nullable=False, default=list
    )  #
    leader_access_rr_roles_ids: Mapped[list[int]] = mapped_column(
        ARRAY(BigInteger), nullable=False, default=list
    )  #
    # embed_config_access_roles: Mapped[list[int] | None] = mapped_column(
    #     ARRAY(BigInteger), nullable=True
    # )


# TODO: feature guild complaint config instead of hardcoded dict
# class GuildComplaintConfig(IdIntegerMixin, Base):
#     guild_id: Mapped[int] = mapped_column(
#         BigInteger, nullable=False, unique=True
#     )


class GuildNotificationsConfig(IdIntegerMixin, Base):  #
    """Notifications configuration for a guild."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    notifications_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    notifications_for_moderation_channel_id: Mapped[int | None] = (
        mapped_column(BigInteger, nullable=True)
    )
    notifications_from_bot_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )


class GuildTicketsConfig(IdIntegerMixin, Base):
    """Tickets configuration for a guild."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    tickets_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    new_tickets_category_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    closed_tickets_category_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    create_ticket_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    pinned_tickets_category_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    create_ticket_ping_role_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )


class GuildInfomakerConfig(IdIntegerMixin, Base):
    """Infomaker configuration for a guild."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    admins_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    leaders_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    admins_roles_logging_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    leaders_roles_logging_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
