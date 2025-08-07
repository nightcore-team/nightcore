"""Guild model for the Nightcore bot database."""

from sqlalchemy import ARRAY, JSON, BigInteger, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models.base import Base
from src.infra.db.models.mixins import IdIntegerMixin


class GuildConfig(IdIntegerMixin, Base):
    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )

    # log channels - все nullable
    ban_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    clan_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    members_update_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    messages_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    voice_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    moderation_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    count_moderator_messages_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    ticket_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    roles_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    channels_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )

    # economy - nullable fields
    coin_name: Mapped[str | None] = mapped_column(String, nullable=True)
    economy_access_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    reward_count: Mapped[float | None] = mapped_column(Float, nullable=True)
    coins_multipler: Mapped[float | None] = mapped_column(Float, nullable=True)
    temp_coins_multipler: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    economy_shop_buy_ping_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    economy_shop: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )
    economy_products: Mapped[dict[str, float]] = mapped_column(
        JSON, nullable=False, default=dict
    )

    # levels - nullable fields
    count_messages_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    level_notify_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    exp_multipler: Mapped[float | None] = mapped_column(Float, nullable=True)
    temp_exp_multipler: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    bonus_roles_ids: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )

    # clans - nullable fields
    clan_payday_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    clan_shop_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    clan_shop_products: Mapped[dict[str, float]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    clan_access_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    create_clan_role_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    clan_buy_ping_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    clan_reputation: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )

    # private rooms - nullable
    private_rooms_create_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )

    # moderation - nullable arrays and scores
    moderation_access_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    ban_access_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
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

    trackable_moderation_role_id: Mapped[str | None] = mapped_column(
        String, nullable=True
    )

    ban_request_ping_role_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    send_ban_request_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )

    # notifications and tickets - nullable
    notifications_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    notifications_for_moderation_channel_id: Mapped[int | None] = (
        mapped_column(BigInteger, nullable=True)
    )
    notifications_from_bot_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
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
    check_role_requests_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    create_ticket_ping_role_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )

    # counts with defaults
    tickets_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    proposals_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    create_proposal_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )

    # roles and configs
    organizational_roles: Mapped[dict[str, int]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    mpmute_role_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    vmute_role_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    level_roles: Mapped[dict[int, int]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    rules_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    fraction_roles: Mapped[dict[str, int]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    leader_access_roles_ids: Mapped[list[int]] = mapped_column(
        ARRAY(BigInteger), nullable=False, default=list
    )
    clan_improvements: Mapped[list[int]] = mapped_column(
        ARRAY(Integer), nullable=False, default=list
    )
    colors: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    drop_from_cases: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )
    illegal_roles: Mapped[dict[str, int]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    embed_config_access_roles: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    message_log_ignoring_channels_ids: Mapped[list[int] | None] = (
        mapped_column(ARRAY(BigInteger), nullable=True)
    )
    voice_temp_roles: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )
    mute_role_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    mute_type: Mapped[str] = mapped_column(
        String, nullable=False, default="role"
    )
    faq: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
