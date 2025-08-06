# noqa: D100

from datetime import datetime

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Float,
    Integer,
    String,
)
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    declared_attr,
    mapped_column,
)
from sqlalchemy.types import JSON, DateTime, SmallInteger

from src.infra.db.mixins import CreatedAtMixin, IdIntegerMixin


class Base(AsyncAttrs, DeclarativeBase):
    @declared_attr.directive
    def __tablename__(self) -> str:  # noqa: D105
        return f"{self.__name__.lower()}"


class User(IdIntegerMixin, Base):
    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    coins: Mapped[float] = mapped_column(nullable=False, default=0.0)
    level: Mapped[int] = mapped_column(nullable=False, default=0)
    current_exp: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    exp_to_level: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    voice_activity: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    temp_voice_activity: Mapped["datetime | None"] = mapped_column(
        DateTime, nullable=True
    )
    reward_time: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0
    )
    ticket_ban: Mapped[bool] = mapped_column(nullable=False, default=False)
    ban_role_request: Mapped[bool] = mapped_column(
        nullable=False, default=False
    )
    battle_pass_level: Mapped[int] = mapped_column(nullable=False, default=0)
    battle_pass_points: Mapped[float] = mapped_column(
        nullable=False, default=0.0
    )
    inventory: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    def __repr__(self):  # noqa: D105
        return f"<DbUser user_id={self.user_id} guild_id={self.guild_id} coins={self.coins}>"  # noqa: E501


class Punish(IdIntegerMixin, Base):
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    used_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    moderator_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    category: Mapped[str] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(nullable=True)
    duration: Mapped[str] = mapped_column(
        nullable=True
    )  # срок выдачи наказания
    end_time: Mapped[int] = mapped_column(
        nullable=True
    )  # время окончания наказания
    time_now: Mapped[int] = mapped_column(
        nullable=True
    )  # время выдачи наказания

    # def __repr__(self):
    #     return f"<Punish guild_id={self.guild_id} category={self.category} user={self.used_id}>"  # noqa: E501


"""
ClanUser:
- user_id: int
- guild_id: int
- clan_id: int
- is_leader: bool
- is_deputy: bool
"""


class Clan(IdIntegerMixin, Base, CreatedAtMixin):
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    leader_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    deputies: Mapped[list[int]] = mapped_column(
        ARRAY(BigInteger), nullable=False, default=list
    )  # Array of deputy IDs
    coins: Mapped[float] = mapped_column(nullable=False, default=0.0)
    current_exp: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    exp_to_level: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    level: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    ## payday for clan
    max_deputies: Mapped[int] = mapped_column(nullable=False, default=0)
    max_members: Mapped[int] = mapped_column(nullable=False, default=0)
    payday_multipler: Mapped[int] = mapped_column(nullable=False, default=1)
    invite_message: Mapped[str | None] = mapped_column(nullable=True)

    # def __repr__(self):
    #     return f"<DbClan guild_id={self.guild_id} role_id={self.role_id} leader_id={self.leader_id}>"  # noqa: E501


class DbConfig(IdIntegerMixin, Base):
    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    # log channels
    economy_log_channel_id: Mapped[int] = mapped_column(BigInteger)
    private_rooms_log_channel_id: Mapped[int] = mapped_column(BigInteger)
    ban_log_channel_id: Mapped[int] = mapped_column(BigInteger)
    clan_log_channel_id: Mapped[int] = mapped_column(BigInteger)
    members_update_log_channel_id: Mapped[int] = mapped_column(BigInteger)
    messages_log_channel_id: Mapped[int] = mapped_column(BigInteger)
    voice_log_channel_id: Mapped[int] = mapped_column(BigInteger)
    moderation_log_channel_id: Mapped[int] = mapped_column(BigInteger)
    count_moderator_messages_channel_id: Mapped[int] = mapped_column(
        BigInteger
    )
    ticket_log_channel_id: Mapped[int] = mapped_column(BigInteger)
    roles_log_channel_id: Mapped[int] = mapped_column(BigInteger)
    channels_log_channel_id: Mapped[int] = mapped_column(BigInteger)
    # economy
    coin_name: Mapped[str] = mapped_column(String)
    economy_access_roles_ids: Mapped[list[int]] = mapped_column(
        ARRAY(BigInteger)
    )
    reward_count: Mapped[float] = mapped_column(Float)
    coins_multipler: Mapped[float] = mapped_column(Float)
    temp_coins_multipler: Mapped[float] = mapped_column(Float)
    economy_shop_buy_ping_roles_ids: Mapped[list[int]] = mapped_column(
        ARRAY(BigInteger)
    )
    economy_shop: Mapped[dict] = mapped_column(JSON, default=dict)
    economy_products: Mapped[dict[str, float]] = mapped_column(
        JSON, default=dict
    )
    # levels
    count_messages_channel_id: Mapped[int] = mapped_column(BigInteger)
    level_notify_channel_id: Mapped[int] = mapped_column(BigInteger)
    exp_multipler: Mapped[float] = mapped_column(Float)
    temp_exp_multipler: Mapped[float] = mapped_column(Float)
    bonus_roles_ids: Mapped[list[str]] = mapped_column(
        ARRAY(String)
    )  # list of role IDs with bonus exp

    # clans
    clan_payday_channel_id: Mapped[int] = mapped_column(BigInteger)
    clan_shop_channel_id: Mapped[int] = mapped_column(BigInteger)
    clan_shop_products: Mapped[dict[str, float]] = mapped_column(
        JSON, default=dict
    )
    clan_access_roles_ids: Mapped[list[int]] = mapped_column(ARRAY(BigInteger))
    create_clan_role_id: Mapped[int] = mapped_column(BigInteger)
    clan_buy_ping_roles_ids: Mapped[list[int]] = mapped_column(
        ARRAY(BigInteger)
    )
    clan_reputation: Mapped[float] = mapped_column(Float, default=0.0)
    # private rooms
    private_rooms_create_channel_id: Mapped[int] = mapped_column(BigInteger)

    # moderation
    moderation_access_roles_ids: Mapped[list[int]] = mapped_column(
        ARRAY(BigInteger)
    )
    ban_access_roles_ids: Mapped[list[int]] = mapped_column(ARRAY(BigInteger))
    mute_score: Mapped[float] = mapped_column(Float)  # Score for mute actions
    ban_score: Mapped[float] = mapped_column(Float)  # Score for ban actions
    kick_score: Mapped[float] = mapped_column(Float)  # Score for kick actions
    ticket_score: Mapped[float] = mapped_column(
        Float
    )  # Score for ticket actions
    role_request_score: Mapped[float] = mapped_column(
        Float
    )  # Score for role request actions
    role_remove_score: Mapped[float] = mapped_column(
        Float
    )  # Score for role remove actions
    ticket_ban_score: Mapped[float] = mapped_column(
        Float
    )  # Score for ticket ban actions
    mpmute_score: Mapped[float] = mapped_column(
        Float
    )  # Score for message mute actions
    vmute_score: Mapped[float] = mapped_column(
        Float
    )  # Score for voice mute actions
    message_score: Mapped[float] = mapped_column(
        Float
    )  # Score for message actions

    trackable_moderation_role_id: Mapped[str] = mapped_column(
        String
    )  # if this role is in user's roles, bot will track his statistic

    ban_request_ping_role_id: Mapped[int] = mapped_column(BigInteger)
    send_ban_request_channel_id: Mapped[int] = mapped_column(BigInteger)

    notifications_channel_id: Mapped[int] = mapped_column(BigInteger)
    notifications_for_moderation_channel_id: Mapped[int] = mapped_column(
        BigInteger
    )
    notifications_from_bot_channel_id: Mapped[int] = mapped_column(BigInteger)
    new_tickets_category_id: Mapped[int] = mapped_column(BigInteger)
    closed_tickets_category_id: Mapped[int] = mapped_column(BigInteger)
    create_ticket_channel_id: Mapped[int] = mapped_column(BigInteger)
    pinned_tickets_category_id: Mapped[int] = mapped_column(BigInteger)
    check_role_requests_channel_id: Mapped[int] = mapped_column(BigInteger)
    create_ticket_ping_role_id: Mapped[int] = mapped_column(BigInteger)
    tickets_count: Mapped[int] = mapped_column(default=0)
    proposals_count: Mapped[int] = mapped_column(default=0)
    create_proposal_channel_id: Mapped[int] = mapped_column(BigInteger)

    organizational_roles: Mapped[dict[str, int]] = mapped_column(
        JSON, default=dict
    )
    mpmute_role_id: Mapped[int] = mapped_column(BigInteger)
    vmute_role_id: Mapped[int] = mapped_column(BigInteger)
    level_roles: Mapped[dict[int, int]] = mapped_column(JSON, default=dict)
    rules_channel_id: Mapped[int] = mapped_column(BigInteger)
    fraction_roles: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    leader_access_roles_ids: Mapped[list[int]] = mapped_column(
        ARRAY(BigInteger), default=list
    )
    clan_improvements: Mapped[list[int]] = mapped_column(
        ARRAY(Integer), default=list
    )
    colors: Mapped[dict] = mapped_column(JSON, default=dict)
    drop_from_cases: Mapped[list[str]] = mapped_column(ARRAY(String))
    # battle_pass_rewards: Mapped[dict] = mapped_column(JSONB)
    # guild_rules: Mapped[dict] = mapped_column(JSONB)
    illegal_roles: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    # roles that has permissions to use embed config
    embed_config_access_roles: Mapped[list[int]] = mapped_column(
        ARRAY(BigInteger)
    )
    # channels that bot will ignore for logging
    message_log_ignoring_channels_ids: Mapped[list[int]] = mapped_column(
        ARRAY(BigInteger)
    )
    voice_temp_roles: Mapped[dict] = mapped_column(JSON, default=dict)
    mute_role_id: Mapped[int] = mapped_column(BigInteger)
    mute_type: Mapped[str] = mapped_column(default="role")  # role or timeout
    faq: Mapped[dict] = mapped_column(JSON, default=dict)
