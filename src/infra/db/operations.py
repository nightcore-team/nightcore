"""The module contains database operations for the Nightcore bot."""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Final, TypeVar, Union, cast

from sqlalchemy import (
    Boolean,
    ColumnElement,
    Integer,
    Numeric,
    asc,
    bindparam,
    delete,
    exists,
    extract,
    func,
    literal,
    or_,
    select,
    type_coerce,
    update,
)
from sqlalchemy import (
    cast as sa_cast,
)
from sqlalchemy.dialects.postgresql import array, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import (
    InstrumentedAttribute,
    Load,
    joinedload,
    selectinload,
)

from src.config.config import config
from src.infra.db.models import (
    CaseOpenReward,
    CaseOpenSession,
    CasinoBet,
    CasinoGame,
    ChangeStat,
    Clan,
    ClanMember,
    CustomComponent,
    GuildAccessConfig,
    GuildClansConfig,
    GuildEconomyConfig,
    GuildFaqConfig,
    GuildForumConfig,
    GuildInfomakerConfig,
    GuildLevelsConfig,
    GuildLoggingConfig,
    GuildModerationConfig,
    GuildMultipliersConfig,
    GuildNotificationsConfig,
    GuildPrivateChannelsConfig,
    GuildProposalsConfig,
    GuildRoleRequestConfig,
    GuildRulesConfig,
    GuildTicketsConfig,
    LoggingRevision,
    ModerationMessage,
    NotifyState,
    PrivateRoomState,
    Punish,
    RoleRequestState,
    ShopOrderState,
    TempEconomyMultiplier,
    TempPunish,
    TempRole,
    TicketState,
    TransferHistory,
    User,
    UserGlobalBadge,
    UserGuildBadge,
)
from src.infra.db.models._annot import (
    ModerationStatsResultAnnot,
)
from src.infra.db.models.badge import GlobalBadge, GuildBadge
from src.infra.db.models.bank import BankAccount, Deposit, ExtraWallet
from src.infra.db.models.battlepass_level import BattlepassLevel
from src.infra.db.models.case import Case
from src.infra.db.models.color import Color
from src.infra.db.models.configurations.clans import GuildClanShopItem
from src.infra.db.models.configurations.economy import GuildEconomyShopItem
from src.infra.db.models.configurations.levels import GuildLevel
from src.infra.db.models.configurations.moderation import GuildFractionRole
from src.infra.db.models.configurations.role_request import (
    GuildOrganizationalRole,
)
from src.infra.db.models.configurations.rules import (
    GuildRules,
    GuildRulesChapter,
    GuildRulesRule,
)
from src.infra.db.models.discord_webhook import DiscordWebhook
from src.infra.db.models.processed_forum_thread import ProcessedForumThread
from src.infra.db.models.rainbow import RainbowRole
from src.infra.db.models.subscription import DiscordGuild
from src.infra.db.models.user import UserVipStatus
from src.infra.db.models.vip import VipStatus
from src.infra.db.utils import (
    build_base_filters as _build_base_moderstats_filters,
)
from src.utils._enums import (
    BadgeTypeEnum,
    CaseOpenSessionStatus,
    CasinoGameStateEnum,
    ChannelType,
    ClanMemberRoleEnum,
    ConfigTypeEnum,
    EntityTypeEnum,
    MultiplierTypeEnum,
    NotifyStateEnum,
    RoleRequestStateEnum,
    TicketStateEnum,
)

GuildT = TypeVar(
    "GuildT",
    GuildClansConfig,
    GuildEconomyConfig,
    GuildLevelsConfig,
    GuildLoggingConfig,
    GuildModerationConfig,
    GuildPrivateChannelsConfig,
    GuildNotificationsConfig,
    GuildTicketsConfig,
    GuildInfomakerConfig,
    GuildAccessConfig,
    GuildProposalsConfig,
    GuildRoleRequestConfig,
    GuildFaqConfig,
    GuildRulesConfig,
    GuildMultipliersConfig,
    GuildForumConfig,
)

ConfigType = Union[  # noqa: UP007
    GuildClansConfig
    | GuildEconomyConfig
    | GuildLevelsConfig
    | GuildLoggingConfig
    | GuildModerationConfig
    | GuildPrivateChannelsConfig
    | GuildNotificationsConfig
    | GuildTicketsConfig
    | GuildInfomakerConfig
    | GuildAccessConfig
    | GuildRulesConfig
    | GuildMultipliersConfig
    | GuildProposalsConfig
    | GuildRoleRequestConfig
    | GuildForumConfig
]

CONFIG_MODEL_MAP: dict[ConfigTypeEnum, type[Any]] = {
    ConfigTypeEnum.ECONOMY: GuildEconomyConfig,
    ConfigTypeEnum.LEVELS: GuildLevelsConfig,
    ConfigTypeEnum.CLANS: GuildClansConfig,
    ConfigTypeEnum.PRIVATE_CHANNELS: GuildPrivateChannelsConfig,
    ConfigTypeEnum.MODERATION: GuildModerationConfig,
    ConfigTypeEnum.NOTIFICATIONS: GuildNotificationsConfig,
    ConfigTypeEnum.INFOMAKER: GuildInfomakerConfig,
    ConfigTypeEnum.FORUM: GuildForumConfig,
    ConfigTypeEnum.RULES: GuildRulesConfig,
    ConfigTypeEnum.PROPOSALS: GuildProposalsConfig,
    ConfigTypeEnum.MULTIPLERS: GuildMultipliersConfig,
    ConfigTypeEnum.ROLE_REQUEST: GuildRoleRequestConfig,
    ConfigTypeEnum.TICKETS: GuildTicketsConfig,
    ConfigTypeEnum.LOGGING: GuildLoggingConfig,
    ConfigTypeEnum.ACCESS: GuildAccessConfig,
}

_ACCESS_COLUMNS: Final[
    dict[ConfigTypeEnum, InstrumentedAttribute[list[int] | None]]
] = {
    ConfigTypeEnum.LOGGING: GuildAccessConfig.logging_config_access_roles_ids,
    ConfigTypeEnum.ECONOMY: GuildAccessConfig.economy_config_access_roles_ids,
    ConfigTypeEnum.LEVELS: GuildAccessConfig.levels_config_access_roles_ids,
    ConfigTypeEnum.CLANS: GuildAccessConfig.clans_config_access_roles_ids,
    ConfigTypeEnum.PRIVATE_CHANNELS: GuildAccessConfig.private_channels_config_access_roles_ids,  # noqa: E501
    ConfigTypeEnum.MODERATION: GuildAccessConfig.moderation_config_access_roles_ids,  # noqa: E501
    ConfigTypeEnum.NOTIFICATIONS: GuildAccessConfig.notifications_config_access_roles_ids,  # noqa: E501
    ConfigTypeEnum.INFOMAKER: GuildAccessConfig.infomaker_config_access_roles_ids,  # noqa: E501
    ConfigTypeEnum.FORUM: GuildAccessConfig.forum_config_access_roles_ids,
    ConfigTypeEnum.RULES: GuildAccessConfig.rules_config_access_roles_ids,
    ConfigTypeEnum.PROPOSALS: GuildAccessConfig.proposal_config_access_roles_ids,  # noqa: E501
    ConfigTypeEnum.MULTIPLERS: GuildAccessConfig.multiplers_config_access_roles_ids,  # noqa: E501
    ConfigTypeEnum.ROLE_REQUEST: GuildAccessConfig.org_roles_config_access_roles_ids,  # noqa: E501
    ConfigTypeEnum.TICKETS: GuildAccessConfig.tickets_config_access_roles_ids,
}


ENTITY_MODEL_MAP: dict[EntityTypeEnum, type[Any]] = {
    EntityTypeEnum.VIP_STATUS: VipStatus,
    EntityTypeEnum.CASE: Case,
    EntityTypeEnum.COLOR: Color,
    EntityTypeEnum.BATTLEPASS_LEVEL: BattlepassLevel,
    EntityTypeEnum.GLOBAL_BADGE: GlobalBadge,
    EntityTypeEnum.GUILD_BADGE: GuildBadge,
}

# ENTITY_ACCESS_COLUMNS: Final[
#     dict[EntityTypeEnum, InstrumentedAttribute[list[int] | None]]
# ] = {
#     EntityTypeEnum.VIP_STATUS: (
#         GuildAccessConfig.economy_config_access_roles_ids
#     ),
#     EntityTypeEnum.CASE: (GuildAccessConfig.economy_config_access_roles_ids),
#     EntityTypeEnum.COLOR: (GuildAccessConfig.economy_config_access_roles_ids),  # noqa: E501
#     EntityTypeEnum.BATTLEPASS_LEVEL: (
#         GuildAccessConfig.economy_config_access_roles_ids
#     ),
# }


async def get_specified_entity(
    session: AsyncSession,
    *,
    entity_type: EntityTypeEnum,
    guild_id: int,
    entity_id: int,
    for_update: bool = False,
):
    """Get a specific entity by ID."""
    model = ENTITY_MODEL_MAP.get(entity_type)

    if model is None:
        raise ValueError(f"Unknown entity type: {entity_type}")

    get_stmt = select(model).where(
        model.guild_id == guild_id,
        model.id == entity_id,
    )
    if for_update:
        get_stmt = get_stmt.with_for_update()

    return await session.scalar(get_stmt)


async def get_specified_entities(
    session: AsyncSession,
    *,
    entity_type: EntityTypeEnum,
    guild_id: int,
    entity_ids: list[int],
    for_update: bool = False,
) -> Sequence[Any]:
    """Get multiple entities by IDs in a single query."""
    model = ENTITY_MODEL_MAP.get(entity_type)

    if model is None:
        raise ValueError(f"Unknown entity type: {entity_type}")

    if not entity_ids:
        return []

    get_stmt = select(model).where(
        model.guild_id == guild_id,
        model.id.in_(entity_ids),
    )
    if for_update:
        get_stmt = get_stmt.with_for_update()

    result = await session.execute(get_stmt)
    return result.scalars().all()


async def get_entities_by_type(
    session: AsyncSession,
    *,
    entity_type: EntityTypeEnum,
    guild_id: int,
) -> Sequence[Any]:
    """Get all entities of a specific type for a guild."""
    model = ENTITY_MODEL_MAP.get(entity_type)

    if model is None:
        raise ValueError(f"Unknown entity type: {entity_type}")

    get_stmt = select(model).where(model.guild_id == guild_id)
    result = await session.execute(get_stmt)
    return result.scalars().all()


async def get_specified_guild_config(  # noqa: UP047
    session: AsyncSession,
    *,
    config_type: type[GuildT],
    guild_id: int,
    for_update: bool = False,
) -> GuildT:
    """Get the guild configuration from the database."""
    get_stmt = select(config_type).where(config_type.guild_id == guild_id)
    if for_update:
        get_stmt = get_stmt.with_for_update()

    config = await session.scalar(get_stmt)

    if config is not None:
        return config

    insert_stmt = (
        insert(config_type)
        .values(guild_id=guild_id)
        .on_conflict_do_nothing()
        .returning(config_type)
    )

    result = await session.execute(insert_stmt)
    config = result.scalar_one_or_none()

    if config is None:
        if for_update:
            get_stmt = get_stmt.with_for_update()
        config = await session.scalar(get_stmt)
        return config  # type: ignore

    if for_update:
        # lock the newly inserted row for R-M-W
        get_stmt = (
            select(config_type)
            .where(config_type.guild_id == guild_id)
            .with_for_update()
        )
        config = await session.scalar(get_stmt)  # type: ignore
        return config  # type: ignore

    return config


async def get_available_guild_configs(
    session: AsyncSession, *, guild_id: int, roles: list[int]
) -> list[str]:
    """Get the list of available guild configurations for the given roles."""

    select_clauses = [
        array(roles).overlap(column).label(config_type.value)
        for config_type, column in _ACCESS_COLUMNS.items()
    ]

    stmt = select(*select_clauses).where(
        GuildAccessConfig.guild_id == guild_id
    )

    result = await session.execute(stmt)
    row = result.mappings().first()

    if row is None:
        return []

    return [key for key, value in row.items() if value]


async def has_guild_config_access(
    session: AsyncSession,
    *,
    guild_id: int,
    roles: list[int],
    config_type: ConfigTypeEnum,
) -> bool:
    """Check if the given roles have access to a guild configuration."""

    target_column = _ACCESS_COLUMNS.get(config_type)

    if target_column is None:
        raise ValueError(f"Unknown config type: {config_type}")

    stmt = select(
        type_coerce(target_column.op("&&")(array(roles)), Boolean)
    ).where(GuildAccessConfig.guild_id == guild_id)

    return bool(await session.scalar(stmt))


async def get_guild_rules(
    session: AsyncSession, *, guild_id: int
) -> GuildRules | None:
    """Get the guild rules from the database."""
    stmt = (
        select(GuildRules)
        .where(GuildRules.guild_id == guild_id)
        .options(
            selectinload(GuildRules.chapters)
            .selectinload(GuildRulesChapter.rules)
            .selectinload(GuildRulesRule.subrules)
        )
    )
    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def get_specified_channel(  # noqa: UP047
    session: AsyncSession,
    *,
    guild_id: int,
    config_type: type[GuildT],
    channel_type: ChannelType,
) -> int | None:
    """Get the specified channel ID from the database."""
    column = getattr(config_type, channel_type.value)
    stmt = select(column).where(config_type.guild_id == guild_id)
    return await session.scalar(stmt)


async def get_specified_webhook(  # noqa: UP047
    session: AsyncSession,
    *,
    guild_id: int,
    config_type: type[GuildT],
    channel_type: ChannelType,
) -> DiscordWebhook | None:
    """Get the specified logging webhook from the database."""

    relationship = getattr(config_type, channel_type.value)
    stmt = (
        select(DiscordWebhook)
        .select_from(config_type)
        .join(relationship)
        .where(config_type.guild_id == guild_id)
    )
    return await session.scalar(stmt)


async def get_specified_field(  # noqa: UP047
    session: AsyncSession,
    *,
    guild_id: int,
    config_type: type[GuildT],
    field_name: str,
    for_update: bool = False,
) -> Any:
    """Get the specified field from the database."""
    column = getattr(config_type, field_name)
    stmt = select(column).where(config_type.guild_id == guild_id)
    if for_update:
        stmt = stmt.with_for_update()
    return await session.scalar(stmt)


async def get_moderation_access_roles(
    session: AsyncSession, *, guild_id: int
) -> list[int]:
    """Get the list of moderation access roles for a guild."""
    stmt = select(GuildModerationConfig.moderation_access_roles_ids).where(
        GuildModerationConfig.guild_id == guild_id
    )
    result = await session.scalar(stmt)
    return result or []


async def get_all_pending_notifications(
    session: AsyncSession,
    now: datetime,
) -> Sequence[NotifyState]:
    """Get all pending notifications."""
    stmt = (
        select(NotifyState)
        .where(
            NotifyState.state == NotifyStateEnum.PENDING,
            NotifyState.end_time < now,
        )
        .with_for_update(skip_locked=True)
    )
    result = await session.scalars(stmt)
    return result.all()


async def get_shop_order_state(
    session: AsyncSession,
    *,
    guild_id: int,
    custom_id: int,
    for_update: bool = False,
) -> ShopOrderState | None:
    """Get the shop order state from the database."""
    stmt = select(ShopOrderState).where(
        ShopOrderState.guild_id == guild_id,
        ShopOrderState.custom_id == custom_id,
    )
    if for_update:
        stmt = stmt.with_for_update()
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_head_moderation_access_roles(
    session: AsyncSession, *, guild_id: int
) -> list[int]:
    """Get the list of head moderation access roles for a guild."""
    stmt = select(GuildModerationConfig.leadership_access_roles_ids).where(
        GuildModerationConfig.guild_id == guild_id
    )
    result = await session.scalar(stmt)
    return result or []


async def is_user_ticketbanned(
    session: AsyncSession, *, guild_id: int, user_id: int
) -> bool:
    """Check if a user is ticket banned in a guild."""
    stmt = select(
        exists().where(
            User.guild_id == guild_id,
            User.user_id == user_id,
            User.ticket_ban.is_(True),
        )
    )
    return bool(await session.scalar(stmt))


async def get_or_create_user(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
    options: list[Load] | None = None,
    for_update: bool = False,
) -> tuple[User, bool]:
    """Get or create a user in the database.

    When `options` is given, its eager-loading options are applied to the
    SELECT so only the requested relations (e.g. cases, colors) are loaded.

    When `for_update` is True the selected row is locked with
    `SELECT ... FOR UPDATE` to prevent concurrent read-modify-write
    races (economy, moderation, voice, etc.).
    """
    get_stmt = select(User).where(
        User.guild_id == guild_id, User.user_id == user_id
    )

    if options:
        get_stmt = get_stmt.options(*options)

    if for_update:
        get_stmt = get_stmt.with_for_update()

    user = await session.scalar(get_stmt)

    if user is not None:
        return user, False

    insert_stmt = (
        insert(User)
        .values(guild_id=guild_id, user_id=user_id)
        .on_conflict_do_nothing(constraint="ux_user_guild_user")
        .returning(User)
    )

    result = await session.execute(insert_stmt)
    user = result.scalar_one_or_none()

    # race condition: between select and insert
    if user is None:
        # re-select with lock if requested
        if for_update:
            get_stmt = get_stmt.with_for_update()
        user = await session.scalar(get_stmt)
        return user, False  # type: ignore[return-value]

    # newly inserted row — RETURNING doesn't apply eager-load options,
    # so re-select whenever options were requested, and/or lock if needed.
    if options or for_update:
        reselect_stmt = select(User).where(
            User.guild_id == guild_id, User.user_id == user_id
        )
        if options:
            reselect_stmt = reselect_stmt.options(*options)
        if for_update:
            reselect_stmt = reselect_stmt.with_for_update()

        user = await session.scalar(reselect_stmt)

    return user, True  # type: ignore[return-value]


async def get_user_vip_statuses_for_update(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
    options: list[Load] | None = None,
    for_update: bool = True,
) -> Sequence[UserVipStatus]:
    """Get the user's all VIP statuses row.

    `UserVipStatus.vip` is lazy, so a caller that reads it has to ask for
    it through `options` - a lazy load on an AsyncSession raises
    MissingGreenlet.

    Locking the UserVipStatus row itself (not the parent User row) is what
    lets this contend with the expiry task, which locks the same rows in
    get_expired_user_vip_statuses_for_update when clearing expired
    statuses — preventing a grant and an expiry cleanup from racing on the
    same user. The caller must therefore filter the expired rows out when
    it needs the ones the user actually holds.
    """

    stmt = select(UserVipStatus).where(
        UserVipStatus.user_id == user_id, UserVipStatus.guild_id == guild_id
    )

    if options:
        stmt = stmt.options(*options)

    if for_update:
        stmt = stmt.with_for_update()

    result = await session.execute(stmt)

    return result.scalars().all()


async def create_case_open_session(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
    case_id: int,
    expires_at: datetime,
    rewards: Sequence[dict[str, Any]],
) -> CaseOpenSession:
    """Create a pending case session and bulk-insert its rewards."""

    case_session = CaseOpenSession(
        guild_id=guild_id,
        user_id=user_id,
        case_id=case_id,
        expires_at=expires_at,
    )
    session.add(case_session)
    await session.flush()

    await session.execute(
        insert(CaseOpenReward),
        [
            {
                "session_id": case_session.id,
                "position": position,
                "reward": reward,
                "reroll_count": 0,
            }
            for position, reward in enumerate(rewards)
        ],
    )

    return case_session


async def get_case_open_session_for_update(
    session: AsyncSession, *, session_id: int, for_update: bool = True
) -> CaseOpenSession | None:
    """Get a case session with a row lock."""

    stmt = select(CaseOpenSession).where(CaseOpenSession.id == session_id)

    if for_update:
        stmt = stmt.with_for_update()

    return await session.scalar(stmt)


async def get_pending_case_open_session(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
) -> CaseOpenSession | None:
    """Get the user's pending case session."""

    stmt = select(CaseOpenSession).where(
        CaseOpenSession.guild_id == guild_id,
        CaseOpenSession.user_id == user_id,
        CaseOpenSession.status == CaseOpenSessionStatus.PENDING,
    )
    return await session.scalar(stmt)


async def get_case_open_rewards_for_update(
    session: AsyncSession,
    *,
    session_id: int,
    reward_id: int | None = None,
) -> Sequence[CaseOpenReward]:
    """Get pending session rewards with row locks."""

    stmt = select(CaseOpenReward).where(
        CaseOpenReward.session_id == session_id
    )
    if reward_id is not None:
        stmt = stmt.where(CaseOpenReward.id == reward_id)
    stmt = stmt.order_by(CaseOpenReward.position).with_for_update()
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_expired_case_open_sessions_for_update(
    session: AsyncSession,
    *,
    now: datetime,
    limit: int = 100,
) -> Sequence[CaseOpenSession]:
    """Get expired pending case sessions in a bounded locked batch."""

    stmt = (
        select(CaseOpenSession)
        .where(
            CaseOpenSession.status == CaseOpenSessionStatus.PENDING,
            CaseOpenSession.expires_at <= now,
        )
        .order_by(CaseOpenSession.expires_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def delete_case_open_sessions(
    session: AsyncSession,
    *,
    session_ids: Sequence[int],
) -> None:
    """Delete case sessions and their rewards cascade."""

    stmt = delete(CaseOpenSession).where(CaseOpenSession.id.in_(session_ids))
    await session.execute(stmt)


async def get_expired_user_vip_statuses_for_update(
    session: AsyncSession,
    *,
    now: datetime,
    options: list[Load] | None = None,
    limit: int = 100,
) -> Sequence[UserVipStatus]:
    """Get expired VIP statuses in a bounded locked batch.

    Locks the very rows get_user_vip_statuses_for_update locks on the grant
    path, so a grant that is extending an expired VIP either wins and the
    cleanup skips the row, or the cleanup deletes it and the grant inserts a
    fresh one.
    """

    stmt = (
        select(UserVipStatus)
        .where(
            UserVipStatus.expires_at.is_not(None),
            UserVipStatus.expires_at <= now,
        )
        .order_by(UserVipStatus.expires_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )

    if options:
        stmt = stmt.options(*options)

    result = await session.execute(stmt)
    return result.scalars().all()


async def delete_user_vip_statuses(
    session: AsyncSession,
    *,
    status_ids: Sequence[int],
) -> None:
    """Delete the given VIP statuses by primary key."""

    if not status_ids:
        return

    stmt = delete(UserVipStatus).where(UserVipStatus.id.in_(status_ids))
    await session.execute(stmt)


async def get_active_user_vip_statuses(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
) -> Sequence[VipStatus]:
    """Get the user's currently granted VIP configurations.

    `is_active` says which of the user's VIPs is the one in use - the
    activation handler moves the flag over when another is activated, and
    the unique index on (guild_id, user_id) where is_active keeps it to a
    single row - but it says nothing about the VIP still being valid. The
    `expires_at` check is what actually ends the bonus.
    """

    stmt = (
        select(VipStatus)
        .join(
            UserVipStatus,
            UserVipStatus.vip_id == VipStatus.id,
        )
        .where(
            UserVipStatus.guild_id == guild_id,
            UserVipStatus.user_id == user_id,
            UserVipStatus.is_active.is_(True),
            or_(
                UserVipStatus.expires_at.is_(None),
                UserVipStatus.expires_at > func.now(),
            ),
        )
    )

    result = await session.execute(stmt)
    return result.scalars().all()


def _get_effective_deposit_config(
    config: GuildEconomyConfig | None,
    vip_statuses: Sequence[VipStatus],
) -> tuple[Decimal, int, int]:
    """Resolve deposit settings from guild config and active VIP statuses."""

    if config is None:
        interest_rate = Decimal("0")
        max_balance = 0
        interest_cap = 0
    else:
        interest_rate = config.deposit_base_interest_rate
        max_balance = config.deposit_max_balance
        interest_cap = config.deposit_interest_cap_amount

    for vip_status in vip_statuses:
        if vip_status.deposit_interest_rate:
            interest_rate = max(
                interest_rate, vip_status.deposit_interest_rate
            )
        if vip_status.deposit_max_balance:
            max_balance = max(max_balance, vip_status.deposit_max_balance)
        if vip_status.deposit_interest_cap_amount:
            interest_cap = max(
                interest_cap, vip_status.deposit_interest_cap_amount
            )

    return interest_rate, max_balance, interest_cap


async def get_effective_deposit_max_balance(
    session: AsyncSession,
    *,
    config: GuildEconomyConfig | None,
    guild_id: int,
    user_id: int,
) -> int:
    """Get the deposit ceiling for the user, 0 meaning there is none.

    Resolved the same way the accrual resolves it, so a VIP that raises the
    ceiling lets the user top the deposit up to it, not only accrue up to it.
    """

    active_vip_statuses = await get_active_user_vip_statuses(
        session,
        guild_id=guild_id,
        user_id=user_id,
    )
    _, max_balance, _ = _get_effective_deposit_config(
        config, active_vip_statuses
    )

    return max_balance


def _apply_deposit_max_balance(
    grown: Decimal, coins: int, max_balance: int
) -> int:
    """Cap a grown deposit at `max_balance` without ever destroying principal.

    A deposit can legitimately end up above `max_balance`: the VIP that
    raised the cap expired, or an admin lowered the guild cap. Clamping
    unconditionally would silently delete the difference, so the balance
    is only ever allowed to grow - over the cap it simply stops accruing.
    """

    if max_balance > 0 and grown > max_balance:
        return max(coins, max_balance)

    return int(grown)


async def accrue_deposit_interest_if_due(
    session: AsyncSession,
    *,
    deposit: Deposit,
    guild_id: int,
    user_id: int,
    config: GuildEconomyConfig | None,
) -> Deposit:
    """Apply pending interest to a single deposit if at least one hour has passed since the last accrual.

    Interest formula: only the portion of the balance up to
    `deposit_interest_cap_amount` compounds each hour (the "base"); any
    amount above that cap ("excess") is parked and doesn't itself grow,
    but still receives the fixed hourly yield generated by the capped
    base. `deposit_max_balance`, if set, is an outer ceiling applied to
    the final result.

        base     = min(coins, cap)
        excess   = max(coins - cap, 0)
        new_coins = base * (1 + rate) ** hours + excess
        final     = min(new_coins, max_balance)   # if max_balance set

    The balance and `last_accrued_at` are read from the row *after*
    locking it, so `hours_elapsed` and `coins` always come from the same
    locked snapshot. Deriving `hours_elapsed` from a value loaded before
    the lock is what used to let two transactions accrue the same hour
    twice: the transaction that lost the row-lock race re-ran the formula
    on the already-grown balance with its own stale `hours_elapsed`.
    """  # noqa: E501

    locked_row = (
        await session.execute(
            select(Deposit.coins, Deposit.last_accrued_at)
            .where(Deposit.id == deposit.id)
            .with_for_update()
        )
    ).one_or_none()

    if locked_row is None:
        return deposit

    coins, last_accrued_at = locked_row

    now = datetime.now(UTC)
    hours_elapsed = int((now - last_accrued_at).total_seconds() // 3600)

    if hours_elapsed <= 0:
        return deposit

    active_vip_statuses = await get_active_user_vip_statuses(
        session,
        guild_id=guild_id,
        user_id=user_id,
    )
    rate, max_balance, cap = _get_effective_deposit_config(
        config, active_vip_statuses
    )

    if not rate:
        deposit.last_accrued_at = now
        return deposit

    base = min(coins, cap) if cap > 0 else coins
    excess = max(coins - cap, 0) if cap > 0 else 0

    new_coins = base * (1 + rate) ** hours_elapsed + excess

    deposit.coins = _apply_deposit_max_balance(new_coins, coins, max_balance)
    deposit.last_accrued_at = now

    return deposit


async def close_out_deposits_before_rate_change(
    session: AsyncSession, *, config: GuildEconomyConfig | None, guild_id: int
) -> int:
    """Force-accrue interest on every deposit in the guild, using the CURRENT config, right before it gets overwritten with a new rate.

    Same base/excess/cap formula as `accrue_deposit_interest_if_due`.
    Each deposit gets its own `hours_elapsed` (time since its own
    `last_accrued_at`), so this is a bulk UPDATE per settings group via
    bindparam/executemany, not a naive `WHERE id IN (...)` (which
    would incorrectly apply one shared hours_elapsed to every row).

    The UPDATEs run on the Core connection: handed a list of parameter
    sets, `session.execute` turns an ORM `update()` into "bulk UPDATE by
    primary key", which refuses the custom WHERE and per-row bind names
    used here. The deposits are read as plain columns for the same reason,
    so no ORM object is left in the session with a balance the Core UPDATE
    has already changed underneath it.

    Returns the number of deposits actually updated.
    """  # noqa: E501

    now = datetime.now(UTC)

    deposit_rows = (
        await session.execute(
            select(Deposit.id, Deposit.last_accrued_at, BankAccount.user_id)
            .join(BankAccount, Deposit.bank_account_id == BankAccount.id)
            .where(BankAccount.guild_id == guild_id)
            .with_for_update(of=Deposit)
        )
    ).all()

    active_vips_result = await session.execute(
        select(VipStatus, UserVipStatus.user_id)
        .join(UserVipStatus, UserVipStatus.vip_id == VipStatus.id)
        .where(
            UserVipStatus.guild_id == guild_id,
            UserVipStatus.is_active.is_(True),
            # same expiry rule as get_active_user_vip_statuses
            or_(
                UserVipStatus.expires_at.is_(None),
                UserVipStatus.expires_at > now,
            ),
        )
    )
    active_vips_by_user: dict[int, list[VipStatus]] = {}
    for vip_status, user_id in active_vips_result.all():
        active_vips_by_user.setdefault(user_id, []).append(vip_status)

    params_by_settings: dict[
        tuple[Decimal, int, int], list[dict[str, int]]
    ] = {}
    no_rate_ids: list[int] = []

    for deposit_id, last_accrued_at, user_id in deposit_rows:
        hours_elapsed = int((now - last_accrued_at).total_seconds() // 3600)
        if hours_elapsed <= 0:
            continue

        rate, max_balance, cap = _get_effective_deposit_config(
            config, active_vips_by_user.get(user_id, [])
        )
        if not rate:
            # No rate configured means no interest at all, so the elapsed
            # hours must not pile up: accrue_deposit_interest_if_due drops
            # them the same way, and leaving them here would hand the user
            # every hour of the unconfigured period as soon as a rate is
            # set again.
            no_rate_ids.append(deposit_id)
            continue

        params_by_settings.setdefault((rate, max_balance, cap), []).append(
            {"deposit_id": deposit_id, "hours_p": hours_elapsed}
        )

    connection = await session.connection()

    if no_rate_ids:
        await connection.execute(
            update(Deposit)
            .where(Deposit.id.in_(no_rate_ids))
            .values(last_accrued_at=now)
        )

    for (rate, max_balance, cap), rows in params_by_settings.items():
        rate_param = bindparam("rate_p", value=rate, type_=Numeric(5, 4))
        cap_param = bindparam("cap_p", value=cap, type_=Integer)
        if cap > 0:
            base_expr = func.least(Deposit.coins, cap_param)
            excess_expr = func.greatest(Deposit.coins - cap_param, 0)
        else:
            base_expr = Deposit.coins
            excess_expr = 0

        grown_expr = func.floor(
            base_expr
            * func.power(
                1 + rate_param,
                bindparam("hours_p", type_=Integer),
            )
            + excess_expr
        )
        if max_balance:
            grown_expr = func.least(
                grown_expr,
                bindparam("max_balance_p", value=max_balance, type_=Integer),
            )

        stmt = (
            update(Deposit)
            .where(Deposit.id == bindparam("deposit_id"))
            .values(
                # greatest(...): never let the result fall below the
                # current balance (see _apply_deposit_max_balance)
                coins=sa_cast(
                    func.greatest(grown_expr, Deposit.coins), Integer
                ),
                last_accrued_at=now,
            )
        )
        # executemany doesn't report a reliable rowcount on asyncpg, and
        # every row here is a deposit locked above, so each one is updated
        await connection.execute(stmt, rows)

    return len(no_rate_ids) + sum(
        len(rows) for rows in params_by_settings.values()
    )


async def get_or_create_bank_account(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
    for_update: bool = False,
) -> tuple[BankAccount, bool]:
    """Get or create a bank account with its deposit.

    The BankAccount and Deposit are created atomically within
    the caller's transaction.

    Returns:
        tuple[BankAccount, bool]:
            The bank account and whether it was newly created.
    """

    get_stmt = (
        select(BankAccount)
        .where(
            BankAccount.guild_id == guild_id,
            BankAccount.user_id == user_id,
        )
        .options(
            selectinload(BankAccount.deposit),
        )
    )

    if for_update:
        get_stmt = get_stmt.with_for_update()

    bank_account = await session.scalar(get_stmt)

    if bank_account is not None:
        return bank_account, False

    # Try to create the BankAccount.
    insert_account_stmt = (
        insert(BankAccount)
        .values(
            guild_id=guild_id,
            user_id=user_id,
        )
        .on_conflict_do_nothing(
            constraint="ux_user_guild_bank_account",
        )
        .returning(BankAccount)
    )

    result = await session.execute(insert_account_stmt)
    bank_account = result.scalar_one_or_none()

    if bank_account is None:
        # Another transaction created the account.
        #
        # Re-select it. If for_update=True, wait for and lock
        # the committed account before using it.
        if for_update:
            get_stmt = get_stmt.with_for_update()

        bank_account = await session.scalar(get_stmt)

        return bank_account, False  # type: ignore[return-value]

    # We created the account, so create its deposit
    # in the same transaction.
    await session.execute(
        insert(Deposit).values(
            bank_account_id=bank_account.id,
            coins=0,
        )
    )

    # Load the relationship before returning.
    bank_account.deposit = await session.scalar(
        select(Deposit).where(
            Deposit.bank_account_id == bank_account.id,
        )
    )

    return bank_account, True


async def create_extra_wallet(
    session: AsyncSession,
    bank_account_id: int,
    coins: int = 0,
    max_wallets: int | None = None,
) -> ExtraWallet | None:
    """Create a new extra wallet, or return None if `max_wallets` is reached.

    The limit is checked here, under the bank account row lock, because
    a caller cannot check it reliably on its own: the count it would read
    comes from a relationship loaded before this lock, so two concurrent
    requests would both pass the check and both create a wallet.
    """

    await session.execute(
        select(BankAccount.id)
        .where(BankAccount.id == bank_account_id)
        .with_for_update()
    )

    wallets_count, max_slot = (
        await session.execute(
            select(
                func.count(ExtraWallet.id),
                func.max(ExtraWallet.slot),
            ).where(ExtraWallet.bank_account_id == bank_account_id)
        )
    ).one()

    if max_wallets is not None and wallets_count >= max_wallets:
        return None

    wallet = ExtraWallet(
        bank_account_id=bank_account_id,
        coins=coins,
        slot=max_slot + 1 if max_slot else 1,
    )
    session.add(wallet)

    return wallet


async def get_user_deposit_for_update(
    session: AsyncSession,
    *,
    bank_account_id: int,
    guild_id: int,
    user_id: int,
    config: GuildEconomyConfig | None = None,
) -> Deposit | None:
    """Get the deposit belonging to the given bank account, applying any pending interest accrual first.

    Always locked: `accrue_deposit_interest_if_due` needs the row lock
    regardless of whether the caller intends to mutate the balance.
    """  # noqa: E501

    stmt = (
        select(Deposit)
        .where(Deposit.bank_account_id == bank_account_id)
        .with_for_update()
    )

    deposit = await session.scalar(stmt)
    if deposit is None:
        return None

    if config is None:
        config = await session.scalar(
            select(GuildEconomyConfig).where(
                GuildEconomyConfig.guild_id == guild_id
            )
        )

    return await accrue_deposit_interest_if_due(
        session,
        deposit=deposit,
        guild_id=guild_id,
        user_id=user_id,
        config=config,
    )


async def get_user_extra_wallet_for_update(
    session: AsyncSession,
    *,
    bank_account_id: int,
    wallet_id: int,
    for_update: bool = True,
) -> ExtraWallet | None:
    """Get a specific extra wallet, scoped to its owning bank account.

    Ownership is enforced via the WHERE clause (bank_account_id),
    not just wallet_id — this prevents locking/using a wallet that
    was passed in but belongs to a different account.
    """

    stmt = select(ExtraWallet).where(
        ExtraWallet.id == wallet_id,
        ExtraWallet.bank_account_id == bank_account_id,
    )

    if for_update:
        stmt = stmt.with_for_update()

    return await session.scalar(stmt)


async def delete_extra_wallet(
    session: AsyncSession,
    *,
    bank_account_id: int,
    wallet_id: int,
) -> None:
    """Delete an extra wallet scoped to its owning bank account.

    Ownership is enforced via the WHERE clause, the same way
    `get_user_extra_wallet_for_update` does it.
    """

    stmt = delete(ExtraWallet).where(
        ExtraWallet.id == wallet_id,
        ExtraWallet.bank_account_id == bank_account_id,
    )
    await session.execute(stmt)


async def get_user_for_update(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
    options: list[Load] | None = None,
    for_update: bool = True,
) -> User | None:
    """Get user row with FOR UPDATE lock (no creation)."""
    stmt = select(User).where(
        User.guild_id == guild_id, User.user_id == user_id
    )

    if options:
        stmt = stmt.options(*options)

    if for_update:
        stmt = stmt.with_for_update()

    return await session.scalar(stmt)


async def try_deduct_user_coins(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
    amount: int,
) -> bool:
    """Atomically deduct coins if balance suffices (CAS).

    Uses `UPDATE ... WHERE coins >= :amount` to avoid TOCTOU.
    Returns True if deducted, False otherwise.
    """
    stmt = (
        update(User)
        .where(
            User.guild_id == guild_id,
            User.user_id == user_id,
            User.coins >= amount,
        )
        .values(coins=User.coins - amount)
        .returning(User.id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


# TODO: rewrite to use all models (like in get_specified_guild_config)
async def set_user_field_upsert(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
    field: str,
    value: bool,
) -> None:
    """Set a field for a user in the database, creating the user if necessary."""  # noqa: E501
    stmt = (
        insert(User)
        .values(guild_id=guild_id, user_id=user_id, **{field: value})
        .on_conflict_do_update(
            constraint="ux_user_guild_user",
            set_={field: value},
        )
    )
    await session.execute(stmt)


async def create_punish(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
    moderator_id: int,
    category: str,
    time_now: datetime,
    reason: str | None = None,
    original_duration: str | None = None,
    duration: int | None = None,
    end_time: datetime | None = None,
) -> Punish:
    """Create a new punishment entry in the database."""

    punish = Punish(
        guild_id=guild_id,
        user_id=user_id,
        moderator_id=moderator_id,
        category=category,
        reason=reason,
        time_now=time_now,
        duration=duration,
        end_time=end_time,
        original_duration=original_duration,
    )
    session.add(punish)
    return punish


async def get_users_by_spec(
    session: AsyncSession,
    *,
    guild_id: int,
    spec: str | None = None,
) -> Sequence[User]:
    """Get users for a guild ordered by the specified spec."""

    stmt = select(User).where(User.guild_id == guild_id).limit(10)

    match spec:
        case "voice" | "voice_activity":
            stmt = stmt.order_by(User.voice_activity.desc())

        case "coins":
            stmt = stmt.order_by(User.coins.desc())

        case "level":
            stmt = stmt.order_by(User.level.desc(), User.current_exp.desc())

        case "messages":
            stmt = stmt.order_by(User.messages_count.desc())

        case "battlepass":
            stmt = stmt.order_by(User.battle_pass_level.desc())

        case "sent":
            stmt = stmt.order_by(User.sended_valentines.desc())

        case "received":
            stmt = stmt.order_by(User.received_valentines.desc())

        case _:
            stmt = stmt.order_by(User.level.desc(), User.current_exp.desc())

    result = await session.scalars(stmt)

    return result.all()


async def create_clan(
    session: AsyncSession, *, guild_id: int, name: str, role_id: int
) -> Clan:
    """Create a new clan in the database."""
    clan = Clan(guild_id=guild_id, name=name, role_id=role_id)
    session.add(clan)
    return clan


async def get_all_clans(
    session: AsyncSession,
) -> Sequence[Clan]:
    """Get all clans from the database."""
    stmt = select(Clan)
    result = await session.scalars(stmt)
    return result.all()


async def create_clan_member(
    session: AsyncSession,
    *,
    guild_id: int,
    clan_id: int,
    user_id: int,
    role: ClanMemberRoleEnum,
) -> ClanMember:
    """Create a new clan member in the database."""
    clan_member = ClanMember(
        guild_id=guild_id, clan_id=clan_id, user_id=user_id, role=role
    )
    session.add(clan_member)
    return clan_member


async def get_clans(session: AsyncSession, *, guild_id: int) -> Sequence[Clan]:
    """Get the list of clans for a guild."""
    stmt = select(Clan).where(Clan.guild_id == guild_id)
    result = await session.scalars(stmt)

    return result.all()


async def get_clans_by_input(
    session: AsyncSession, *, guild_id: int, user_input: str
) -> Sequence[Clan]:
    """Get the list of clans for a guild."""
    a = 0.7
    similarity = (len(user_input) / 100) ** a

    stmt = (
        select(Clan)
        .where(
            Clan.guild_id == guild_id,
            func.similarity(Clan.name, user_input) >= similarity,
        )
        .limit(25)
    )
    result = await session.scalars(stmt)

    return result.all()


async def get_clans_by_spec(
    session: AsyncSession,
    *,
    guild_id: int,
    spec: str | None = None,
    limit: int | None = None,
) -> Sequence[Clan]:
    """Get clans for a guild ordered by the specified spec (e.g., 'reputation' or 'members')."""  # noqa: E501
    stmt = select(Clan).where(Clan.guild_id == guild_id).limit(limit)

    match spec:
        case "members":
            stmt = (
                stmt.join(Clan.members)
                .group_by(Clan.id)
                .order_by(func.count(ClanMember.id).desc())
            )

        case "created_at":
            # Order by a Clan column if it exists, otherwise fall back to id
            stmt = stmt.order_by(Clan.created_at.asc())

        case "reputation":
            stmt = stmt.order_by(Clan.coins.desc())

        case _:
            stmt = stmt.order_by(Clan.id.asc())

    result = await session.scalars(stmt)

    return result.all()


async def get_clan_member(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
    with_relations: bool = False,
    with_clan_members: bool = False,
    for_update: bool = False,
) -> ClanMember | None:
    """Get the clan member configuration from the database."""
    stmt = select(ClanMember).where(
        ClanMember.guild_id == guild_id, ClanMember.user_id == user_id
    )
    if with_relations:
        stmt = stmt.options(
            selectinload(ClanMember.clan).selectinload(Clan.deputies)
        )
    if with_clan_members:
        stmt = stmt.options(
            selectinload(ClanMember.clan).selectinload(Clan.members)
        )
    if for_update:
        stmt = stmt.with_for_update()
    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def get_clan_by_id(
    session: AsyncSession,
    *,
    guild_id: int,
    clan_id: int | None = None,
    for_update: bool = False,
) -> Clan | None:
    """Get clan by id."""
    stmt = select(Clan).where(Clan.guild_id == guild_id)
    if clan_id:
        stmt = stmt.where(Clan.id == clan_id)
    if for_update:
        stmt = stmt.with_for_update()

    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def get_clan_by_name(
    session: AsyncSession,
    *,
    guild_id: int,
    clan_name: str,
    for_update: bool = False,
) -> Clan | None:
    """Get the clan configuration from the database."""

    stmt = select(Clan).where(
        Clan.guild_id == guild_id, Clan.name == clan_name
    )
    if for_update:
        stmt = stmt.with_for_update()
    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def get_user_clan(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
    for_update: bool = False,
) -> Clan | None:
    """Get the clan of a user in a guild."""

    stmt = (
        select(Clan)
        .join(ClanMember, ClanMember.clan_id == Clan.id)
        .where(Clan.guild_id == guild_id, ClanMember.user_id == user_id)
    )
    if for_update:
        stmt = stmt.with_for_update()
    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def get_private_room_state(
    session: AsyncSession, *, user_id: int, for_update: bool = False
) -> PrivateRoomState | None:
    """Get the private room state for a user."""
    stmt = (
        select(PrivateRoomState)
        .where(PrivateRoomState.user_id == user_id)
        .limit(1)
    )
    if for_update:
        stmt = stmt.with_for_update()
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def get_private_room_state_by_channel(
    session: AsyncSession, *, channel_id: int, for_update: bool = False
) -> PrivateRoomState | None:
    """Get the private room state bound to a voice channel."""
    stmt = (
        select(PrivateRoomState)
        .where(PrivateRoomState.channel_id == channel_id)
        .limit(1)
    )
    if for_update:
        stmt = stmt.with_for_update()
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def create_private_room_state(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
    channel_id: int,
) -> PrivateRoomState | None:
    """Create a private room state for a user (idempotent per user).

    Returns the newly inserted row, or ``None`` if a state already
    exists for the user (race condition / duplicate insert).
    """
    stmt = (
        insert(PrivateRoomState)
        .values(
            guild_id=guild_id,
            user_id=user_id,
            channel_id=channel_id,
        )
        .on_conflict_do_nothing(index_elements=["user_id"])
        .returning(PrivateRoomState)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_temp_punish(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
    category: str,
    end_time: datetime,
) -> TempPunish:
    """Create a new temporary punishment entry in the database.

    Idempotent: if an active TempPunish for the same guild/user/category
    already exists (end_time in the future), its end_time is updated
    to the later of the two values instead of inserting a duplicate.
    Uses SELECT ... FOR UPDATE to serialize concurrent inserts.
    """
    # Check for existing active punish with row-level lock
    existing_stmt = (
        select(TempPunish)
        .where(
            TempPunish.guild_id == guild_id,
            TempPunish.user_id == user_id,
            func.lower(TempPunish.category) == category.lower(),
        )
        .order_by(TempPunish.end_time.desc().nulls_last())
        .limit(1)
        .with_for_update()
    )
    res = await session.execute(existing_stmt)
    existing = res.scalar_one_or_none()
    now = datetime.now(UTC)

    if existing is not None and existing.end_time > now:
        # If existing is still active, extend it idempotently
        if end_time > existing.end_time:
            existing.end_time = end_time
        return existing

    temp_punish = TempPunish(
        guild_id=guild_id,
        user_id=user_id,
        category=category,
        end_time=end_time,
    )
    session.add(temp_punish)

    return temp_punish


async def get_expired_temp_infractions(
    session: AsyncSession,
) -> Sequence[TempPunish]:
    """Get the list of expired temporary punishments from the database."""
    stmt = (
        select(TempPunish)
        .where(TempPunish.end_time <= datetime.now(UTC))
        .with_for_update(skip_locked=True)
    )
    result = await session.scalars(stmt)
    return result.all()


async def get_latest_temp_punish(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
    category: str,
    for_update: bool = False,
) -> TempPunish | None:
    """Get the latest temporary punishment for a user in a guild."""
    stmt = (
        select(TempPunish)
        .where(
            TempPunish.guild_id == guild_id,
            TempPunish.user_id == user_id,
            func.lower(TempPunish.category) == category.lower(),
        )
        .order_by(TempPunish.end_time.asc().nulls_last())
        .limit(1)
    )
    if for_update:
        stmt = stmt.with_for_update()
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def get_user_notify_by_end_time(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int | None = None,
    message_id: int | None = None,
    ts: int,
) -> NotifyState | None:
    """Get the notify state for a user in a guild by end time."""
    stmt = (
        select(NotifyState)
        .where(
            NotifyState.guild_id == guild_id,
            func.floor(extract("epoch", NotifyState.end_time)) == ts,
            NotifyState.state == NotifyStateEnum.PENDING,
        )
        .limit(1)
    )
    if user_id:
        stmt = stmt.where(NotifyState.user_id == user_id)
    if message_id:
        stmt = stmt.where(NotifyState.message_id == message_id)

    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def get_ticket_state(
    session: AsyncSession,
    *,
    guild_id: int,
    channel_id: int,
    for_update: bool = False,
) -> TicketState | None:
    """Get the latest ticket state for a user in a guild."""
    stmt = (
        select(TicketState)
        .where(
            TicketState.guild_id == guild_id,
            TicketState.channel_id == channel_id,
        )
        .limit(1)
    )
    if for_update:
        stmt = stmt.with_for_update()

    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def get_user_ticket(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
    for_update: bool = False,
) -> TicketState | None:
    """Get the latest ticket state for a user in a guild."""
    stmt = (
        select(TicketState)
        .where(
            TicketState.guild_id == guild_id,
            TicketState.author_id == user_id,
            TicketState.state.in_(
                (TicketStateEnum.OPENED, TicketStateEnum.PINNED)
            ),
        )
        .limit(1)
    )
    if for_update:
        stmt = stmt.with_for_update()

    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def get_latest_user_role_request(
    session: AsyncSession,
    *,
    guild_id: int | None,
    user_id: int,
    for_update: bool = False,
) -> RoleRequestState | None:
    """Get the latest role request state for a user in a guild."""
    by_guild_id = RoleRequestState.guild_id == guild_id
    by_user_id = RoleRequestState.author_id == user_id
    _clause = [by_user_id]
    if guild_id:
        _clause.append(by_guild_id)
    stmt = (
        select(RoleRequestState)
        .where(*_clause)
        .order_by(
            RoleRequestState.updated_at.desc().nulls_last(),
        )
        .limit(1)
    )
    if for_update:
        stmt = stmt.with_for_update()
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def get_last_logging_revision(
    session: AsyncSession,
    *,
    guild_id: int,
    config_type: ConfigTypeEnum,
    for_update: bool = False,
) -> LoggingRevision | None:
    """Get the most recent logging revision for a guild.

    Args:
        session: The async database session.
        guild_id: The ID of the guild to get the revision for.
        config_type: The type of the configuration to filter by.
        for_update: SELECT ... FOR UPDATE to lock db record.

    Returns:
        The most recent LoggingRevision or None when none exist.
    """

    stmt = (
        select(LoggingRevision)
        .where(
            LoggingRevision.guild_id == guild_id,
            LoggingRevision.config_type == config_type,
        )
        .order_by(
            LoggingRevision.created_at.desc().nulls_last(),
        )
        .limit(1)
    )
    if for_update:
        stmt = stmt.with_for_update()

    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def get_logging_revision_by_id(
    session: AsyncSession,
    *,
    guild_id: int,
    revision_id: str,
    config_type: ConfigTypeEnum,
):
    """Get a single logging revision for a guild.

    Args:
        session: The async database session.
        guild_id: The ID of the guild the revision belongs to.
        revision_id: The revision ID to look up.
        config_type: The type of the configuration the revision belongs to.

    Returns:
        The matching LoggingRevision or None when it is not found.
    """

    stmt = (
        select(LoggingRevision)
        .where(
            LoggingRevision.guild_id == guild_id,
            LoggingRevision.revision_id == revision_id,
            LoggingRevision.config_type == config_type,
        )
        .with_for_update()
    )

    result = await session.execute(stmt)

    return result.scalar_one_or_none()


def _logging_revision_conditions(
    *,
    guild_id: int,
    config_types: Sequence[ConfigTypeEnum] | None,
    user_id: int | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> list[ColumnElement[bool]]:
    """Build the shared filter conditions for logging revision queries."""

    conditions: list[ColumnElement[bool]] = [
        LoggingRevision.guild_id == guild_id,
    ]

    if config_types is not None:
        conditions.append(LoggingRevision.config_type.in_(config_types))

    if user_id is not None:
        conditions.append(LoggingRevision.user_id == user_id)

    if date_from is not None:
        conditions.append(LoggingRevision.created_at >= date_from)

    if date_to is not None:
        conditions.append(LoggingRevision.created_at <= date_to)

    return conditions


async def get_logging_revisions(
    session: AsyncSession,
    *,
    guild_id: int,
    config_types: Sequence[ConfigTypeEnum] | None = None,
    user_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> Sequence[LoggingRevision]:
    """Get logging revisions for a guild.

    Optionally filters by configuration types (``config_types``),
    author (``user_id``) and a ``created_at`` date range
    (``date_from`` / ``date_to``, both inclusive).

    Returns a paginated window of the most recent revisions.
    """

    if config_types is not None and not config_types:
        return []

    conditions = _logging_revision_conditions(
        guild_id=guild_id,
        config_types=config_types,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
    )

    stmt = (
        select(LoggingRevision)
        .where(*conditions)
        .order_by(
            LoggingRevision.created_at.desc().nulls_last(),
        )
        .limit(limit)
        .offset(offset)
    )

    result = await session.execute(stmt)

    return result.scalars().all()


async def count_logging_revisions(
    session: AsyncSession,
    *,
    guild_id: int,
    config_types: Sequence[ConfigTypeEnum] | None = None,
    user_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> int:
    """Count logging revisions matching the same filters as the listing.

    Needed for pagination: the listing itself returns only one page, so the
    total number of matching revisions has to be asked for separately.
    """

    if config_types is not None and not config_types:
        return 0

    conditions = _logging_revision_conditions(
        guild_id=guild_id,
        config_types=config_types,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
    )

    stmt = select(func.count()).select_from(LoggingRevision).where(*conditions)

    return await session.scalar(stmt) or 0


async def delete_expired_logging_revisions(session: AsyncSession) -> None:
    """Delete logging revisions older than 60 days.

    Mirrors :func:`insert_moderation_message`: a single batch (at most 100
    rows, ``FOR UPDATE SKIP LOCKED``) is pruned per call so concurrent
    config updates never block on the cleanup.
    """

    expired_ids = (
        select(LoggingRevision.revision_id)
        .where(
            LoggingRevision.created_at
            <= datetime.now(UTC) - timedelta(days=60)
        )
        .order_by(LoggingRevision.created_at)
        .limit(100)
        .with_for_update(skip_locked=True)
    )
    stmt = delete(LoggingRevision).where(
        LoggingRevision.revision_id.in_(expired_ids)
    )

    await session.execute(stmt)


async def get_fraction_roles(
    session: AsyncSession, *, guild_id: int
) -> Sequence[int]:
    """Get the list of fraction roles for a guild."""

    stmt = select(GuildFractionRole.role_id).where(
        GuildModerationConfig.guild_id == guild_id
    )
    roles = await session.execute(stmt)

    return roles.scalars().all()


async def get_user_infractions(
    session: AsyncSession, *, guild_id: int, user_id: int
) -> Sequence[Punish]:
    """Get the list of punishments for a user in a guild."""
    stmt = (
        select(Punish)
        .where(Punish.guild_id == guild_id)
        .where(Punish.user_id == user_id)
        .order_by(Punish.time_now.asc())
    )
    result = await session.scalars(stmt)

    return result.all()


async def get_moderation_stats(
    session: AsyncSession,
    *,
    guild_id: int,
    moderators: dict[int, str],
    from_date: datetime,
    to_date: datetime,
) -> ModerationStatsResultAnnot:
    """Return infractions grouped by moderator_id."""

    if not moderators:
        return ModerationStatsResultAnnot()  # type: ignore

    moderator_ids = list(moderators.keys())

    # ---- Punishments ----
    punishments_result = await session.scalars(
        select(Punish)
        .where(
            *_build_base_moderstats_filters(
                Punish, guild_id, moderator_ids, from_date, to_date
            )
        )
        .order_by(Punish.moderator_id.asc())
    )
    punishments = punishments_result.all()

    # ---- Tickets ----
    tickets_result = await session.scalars(
        select(TicketState)
        .where(
            *_build_base_moderstats_filters(
                TicketState,
                guild_id,
                moderator_ids,
                from_date,
                to_date,
                "updated_at",
            ),
            TicketState.state.in_(
                [TicketStateEnum.CLOSED, TicketStateEnum.DELETED]
            ),
        )
        .order_by(TicketState.moderator_id.asc())
    )
    tickets = tickets_result.all()

    # ---- Role Requests ----
    role_requests_result = await session.scalars(
        select(RoleRequestState)
        .where(
            *_build_base_moderstats_filters(
                RoleRequestState,
                guild_id,
                moderator_ids,
                from_date,
                to_date,
                "updated_at",
            ),
            RoleRequestState.state == RoleRequestStateEnum.APPROVED,
        )
        .order_by(RoleRequestState.moderator_id.asc())
    )
    role_requests = role_requests_result.all()

    # ---- Change Stats ----
    changestats_result = await session.scalars(
        select(ChangeStat)
        .where(
            *_build_base_moderstats_filters(
                ChangeStat, guild_id, moderator_ids, from_date, to_date
            )
        )
        .order_by(ChangeStat.moderator_id.asc())
    )
    changestats = changestats_result.all()

    # ---- Messages Count ----
    stmt = (
        select(
            ModerationMessage.moderator_id,
            func.count(ModerationMessage.id).label("messages_count"),
        )
        .where(
            *_build_base_moderstats_filters(
                ModerationMessage,
                guild_id,
                moderator_ids,
                from_date,
                to_date,
            )
        )
        .group_by(ModerationMessage.moderator_id)
    )

    notifications = await session.scalars(
        select(NotifyState).where(
            *_build_base_moderstats_filters(
                NotifyState,
                guild_id,
                moderator_ids,
                from_date,
                to_date,
                "end_time",
            ),
            NotifyState.state == NotifyStateEnum.TIMED_OUT,
        )
    )
    notifications = notifications.all()

    result = await session.execute(stmt)
    messages_data = dict(result.all())  # type: ignore

    return {
        "moderators": moderators,
        "punishments": punishments,
        "tickets": tickets,
        "role_requests": role_requests,
        "changestats": changestats,
        "messages": messages_data,  # type: ignore
        "notifications": notifications,
    }


async def get_moderstats_dict(
    session: AsyncSession,
    *,
    guild_id: int,
) -> dict[str, float]:
    """Get a dictionary of moderator stats fields (ending with _score) for a guild."""  # noqa: E501

    stmt = select(GuildModerationConfig).where(
        GuildModerationConfig.guild_id == guild_id
    )
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()
    if not config:
        return {}

    score_fields = [
        column.key
        for column in GuildModerationConfig.__table__.columns
        if column.key.endswith("_score")
    ]

    return {field: getattr(config, field) for field in score_fields}


async def get_temp_role(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
    role_id: int,
    for_update: bool = False,
) -> TempRole | None:
    """Get the temporary role for a user in a guild."""
    stmt = (
        select(TempRole)
        .where(
            TempRole.guild_id == guild_id,
            TempRole.user_id == user_id,
            TempRole.role_id == role_id,
        )
        .limit(1)
    )
    if for_update:
        stmt = stmt.with_for_update()
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def reset_users_battlepass_levels(
    session: AsyncSession,
    *,
    guild_id: int,
) -> int:
    """Reset all users' battlepass levels and points in a guild and return the count of affected users."""  # noqa: E501
    stmt = (
        update(User)
        .values(
            battle_pass_level=1,
            battle_pass_points=0,
        )
        .where(User.guild_id == guild_id)
        .returning(User.user_id)
    )

    result = await session.execute(stmt)
    updated_ids = result.scalars().all()
    return len(updated_ids)


async def reset_guild_battlepass_config(
    session: AsyncSession,
    *,
    guild_id: int,
):
    """Reset the battlepass levels and rewards in the guild configuration."""
    stmt = (
        update(GuildEconomyConfig)
        .values(battlepass_rewards=[])
        .where(GuildEconomyConfig.guild_id == guild_id)
    )

    await session.execute(stmt)


async def create_transfer_money_record(
    session: AsyncSession,
    *,
    guild_id: int,
    sender_id: int,
    receiver_id: int,
    amount: int,
) -> None:
    """Create a transfer money record in the database."""

    record = TransferHistory(
        guild_id=guild_id,
        user_id=sender_id,
        receiver_id=receiver_id,
        amount=amount,
    )
    session.add(record)


async def get_user_transfer_history(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
) -> Sequence[TransferHistory]:
    """Get the transfer history for a user in a guild (both sent and received)."""  # noqa: E501

    # Transfers sent by the user
    stmt_sent = select(TransferHistory).where(
        TransferHistory.guild_id == guild_id,
        TransferHistory.user_id == user_id,
    )

    # Transfers received by the user
    stmt_received = select(TransferHistory).where(
        TransferHistory.guild_id == guild_id,
        TransferHistory.receiver_id == user_id,
    )

    # Combine both queries using union
    stmt = stmt_sent.union_all(stmt_received).order_by(
        TransferHistory.created_at.desc()
    )

    result = await session.execute(
        select(TransferHistory).from_statement(stmt)
    )

    return result.scalars().all()


async def count_user_infractions_last_7_days(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
) -> int:
    """Count the number of punishments for a user in the last 7 days."""
    boundary = datetime.now(UTC) - timedelta(days=7)

    stmt = (
        select(func.count())
        .select_from(Punish)
        .where(
            Punish.guild_id == guild_id,
            Punish.user_id == user_id,
            Punish.time_now.is_not(None),
            Punish.time_now >= boundary,
        )
    )

    result = await session.execute(stmt)
    return result.scalar_one()


async def get_role_requests_to_delete(
    session: AsyncSession,
) -> Sequence[RoleRequestState]:
    """Get role requests that need to be deleted based on their duration."""
    boundary = datetime.now(UTC) - timedelta(
        hours=config.bot.ROLE_REQUESTS_ALIVE_HOURS
    )

    stmt = (
        select(RoleRequestState)
        .where(
            RoleRequestState.state.in_(
                [
                    "pending",
                ]
            ),
            RoleRequestState.updated_at <= boundary,
        )
        .with_for_update(skip_locked=True)
    )

    result = await session.scalars(stmt)
    return result.all()


async def delete_role_requests(
    session: AsyncSession,
    *,
    status_ids: Sequence[int],
) -> None:
    """Delete the given role requests by primary key."""

    if not status_ids:
        return

    stmt = delete(RoleRequestState).where(RoleRequestState.id.in_(status_ids))
    await session.execute(stmt)


async def get_tickets_to_delete(
    session: AsyncSession,
) -> Sequence[TicketState]:
    """Get closed tickets that need to be deleted based on their duration."""
    boundary = datetime.now(UTC) - timedelta(
        hours=config.bot.CLOSED_TICKET_ALIVE_HOURS
    )

    stmt = (
        select(TicketState)
        .where(
            TicketState.state == TicketStateEnum.CLOSED,
            TicketState.updated_at <= boundary,
        )
        .with_for_update(skip_locked=True)
    )

    result = await session.scalars(stmt)
    return result.all()


async def delete_tickets(
    session: AsyncSession,
    *,
    status_ids: Sequence[int],
) -> None:
    """Delete the given tickets by primary key."""

    if not status_ids:
        return

    stmt = delete(TicketState).where(TicketState.id.in_(status_ids))
    await session.execute(stmt)


async def get_all_expired_temp_roles(
    session: AsyncSession,
) -> Sequence[TempRole]:
    """Get all expired temporary roles."""
    stmt = (
        select(TempRole)
        .where(TempRole.end_time <= datetime.now(UTC))
        .with_for_update(skip_locked=True)
    )
    result = await session.scalars(stmt)

    return result.all()


async def delete_temp_roles(
    session: AsyncSession,
    *,
    status_ids: Sequence[int],
) -> None:
    """Delete the given temporary roles by primary key."""

    if not status_ids:
        return

    stmt = delete(TempRole).where(TempRole.id.in_(status_ids))
    await session.execute(stmt)


async def get_total_users_count(session: AsyncSession) -> int:
    """Get the total number of users in the database."""
    stmt = select(func.count()).select_from(User)

    return cast(int, await session.scalar(stmt))


async def get_mute_role(session: AsyncSession, *, guild_id: int) -> int | None:
    """Get the mute role for a guild."""
    stmt = select(GuildModerationConfig.mute_role_id).where(
        GuildModerationConfig.guild_id == guild_id
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_mpmute_role(
    session: AsyncSession, *, guild_id: int
) -> int | None:
    """Get the marketplace mute role for a guild."""
    stmt = select(GuildModerationConfig.mpmute_role_id).where(
        GuildModerationConfig.guild_id == guild_id
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_vmute_role(
    session: AsyncSession, *, guild_id: int
) -> int | None:
    """Get the voice mute role for a guild."""
    stmt = select(GuildModerationConfig.vmute_role_id).where(
        GuildModerationConfig.guild_id == guild_id
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_mute_type(session: AsyncSession, *, guild_id: int) -> str | None:
    """Get the mute type for a guild."""
    stmt = select(GuildModerationConfig.mute_type).where(
        GuildModerationConfig.guild_id == guild_id
    )
    result = await session.execute(stmt)
    scalar = result.scalar_one_or_none()
    return scalar.value if scalar else None


async def get_or_create_temp_multiplier(
    session: AsyncSession,
    *,
    guild_id: int,
    multiplier_type: MultiplierTypeEnum,
    multiplier: int = 1,
    duration: int = 3600,  # 1 година в секундах
    for_update: bool = False,
) -> tuple[TempEconomyMultiplier, bool]:
    """Get or create a temporary economy multiplier for a guild.

    When ``for_update`` is True the existing row (if any) is locked with
    ``SELECT ... FOR UPDATE`` to serialize concurrent read-modify-write.
    """

    stmt = (
        insert(TempEconomyMultiplier)
        .values(
            guild_id=guild_id,
            multiplier_type=multiplier_type,
            multiplier=multiplier,
            duration=duration,
            end_time=datetime.now(UTC) + timedelta(seconds=duration),
        )
        .on_conflict_do_nothing(constraint="ux_temp_multiplier_guild_type")
        .returning(TempEconomyMultiplier.id)
    )
    res = await session.execute(stmt)
    created = res.scalar_one_or_none() is not None

    select_stmt = select(TempEconomyMultiplier).where(
        TempEconomyMultiplier.guild_id == guild_id,
        TempEconomyMultiplier.multiplier_type == multiplier_type,
    )
    if for_update:
        select_stmt = select_stmt.with_for_update()

    entity = await session.scalar(select_stmt)

    return entity, created  # type: ignore


async def get_all_expired_temp_multipliers(
    session: AsyncSession,
) -> Sequence[TempEconomyMultiplier]:
    """Get all expired temporary economy multipliers.

    Returns multipliers where end_time <= current time.
    """
    from datetime import datetime

    now = datetime.now(UTC)

    stmt = (
        select(TempEconomyMultiplier)
        .where(TempEconomyMultiplier.end_time <= now)
        .with_for_update(skip_locked=True)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def delete_temp_multipliers(
    session: AsyncSession,
    *,
    status_ids: Sequence[int],
) -> None:
    """Delete the given temporary multipliers by primary key."""

    if not status_ids:
        return

    stmt = delete(TempEconomyMultiplier).where(
        TempEconomyMultiplier.id.in_(status_ids)
    )
    await session.execute(stmt)


async def get_custom_components(
    session: AsyncSession, *, guild_id: int
) -> Sequence[CustomComponent]:
    """Get the custom components for a guild."""
    stmt = select(CustomComponent).where(CustomComponent.guild_id == guild_id)
    result = await session.execute(stmt)

    return result.scalars().all()


async def get_custom_components_by_input(
    session: AsyncSession, *, guild_id: int, user_input: str
) -> Sequence[CustomComponent]:
    """Get the custom components for a guild by user input."""
    a = 0.7
    similarity = (len(user_input) / 100) ** a

    stmt = (
        select(CustomComponent)
        .where(
            CustomComponent.guild_id == guild_id,
            func.similarity(CustomComponent.name, user_input) >= similarity,
        )
        .limit(25)
    )
    result = await session.scalars(stmt)

    return result.all()


async def get_custom_component_by_id(
    session: AsyncSession, *, guild_id: int, id: int, for_update: bool = False
) -> CustomComponent | None:
    """Get a custom component by name for a guild."""
    stmt = select(CustomComponent).where(
        CustomComponent.guild_id == guild_id, CustomComponent.id == id
    )
    if for_update:
        stmt = stmt.with_for_update()
    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def get_color_by_id(
    session: AsyncSession,
    *,
    guild_id: int,
    color_id: int,
    for_update: bool = False,
) -> Color | None:
    """Get a color by id for a guild."""
    stmt = select(Color).where(
        Color.guild_id == guild_id, Color.id == color_id
    )
    if for_update:
        stmt = stmt.with_for_update()

    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def get_casino_game_by_message_id(
    session: AsyncSession,
    *,
    guild_id: int,
    message_id: int,
    with_bets: bool = False,
    for_update: bool = False,
) -> CasinoGame | None:
    """Get a casino game by message ID for a guild."""
    stmt = select(CasinoGame).where(
        CasinoGame.guild_id == guild_id,
        CasinoGame.message_id == message_id,
    )
    if with_bets:
        stmt = stmt.options(
            selectinload(CasinoGame.bets).selectinload(CasinoBet.user)
        )
    if for_update:
        stmt = stmt.with_for_update()

    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def get_casino_game_for_update(
    session: AsyncSession, *, guild_id: int, message_id: int
) -> CasinoGame | None:
    """Get casino game with FOR UPDATE and bets+user locked."""
    stmt = (
        select(CasinoGame)
        .where(
            CasinoGame.guild_id == guild_id,
            CasinoGame.message_id == message_id,
        )
        .options(selectinload(CasinoGame.bets).selectinload(CasinoBet.user))
        .with_for_update()
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_guild_colors(
    session: AsyncSession, *, guild_id: int
) -> Sequence[Color]:
    """Get colors by guild id."""

    stmt = select(Color).where(Color.guild_id == guild_id)
    result = await session.execute(stmt)

    return result.scalars().all()


async def get_rainbow_role_by_guild(
    session: AsyncSession, *, guild_id: int
) -> RainbowRole | None:
    """Get a rainbow role for a guild."""
    stmt = select(RainbowRole).where(RainbowRole.guild_id == guild_id)

    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def get_due_rainbow_roles(
    session: AsyncSession, *, now: datetime
) -> Sequence[RainbowRole]:
    """Get rainbow roles whose change deadline has arrived or is not set."""
    stmt = (
        select(RainbowRole)
        .where(
            or_(
                RainbowRole.next_change_at.is_(None),
                RainbowRole.next_change_at <= now,
            )
        )
        .with_for_update(skip_locked=True)
    )
    result = await session.execute(stmt)

    return result.scalars().all()


async def update_rainbow_role_schedule(
    session: AsyncSession,
    *,
    guild_id: int,
    next_change_at: datetime | None,
    current_step: int | None,
) -> None:
    """Update a rainbow role's change deadline and offset step."""
    stmt = (
        update(RainbowRole)
        .where(RainbowRole.guild_id == guild_id)
        .values(
            next_change_at=next_change_at,
            current_step=current_step,
        )
    )

    await session.execute(stmt)


async def get_guild_cases(
    session: AsyncSession, *, guild_id: int
) -> Sequence[Case]:
    """Get cases by guild id."""
    stmt = select(Case).where(Case.guild_id == guild_id)
    result = await session.execute(stmt)

    return result.scalars().all()


async def get_guild_vip_statuses(
    session: AsyncSession, *, guild_id: int
) -> Sequence[VipStatus]:
    """Get VIP-statuses by guild id."""
    stmt = select(VipStatus).where(VipStatus.guild_id == guild_id)
    result = await session.execute(stmt)

    return result.scalars().all()


async def get_cases_by_input(
    session: AsyncSession, *, guild_id: int, user_input: str
) -> Sequence[Case]:
    """Get the list of cases for a guild by user input."""
    a = 0.7
    similarity = (len(user_input) / 100) ** a

    stmt = (
        select(Case)
        .where(
            Case.guild_id == guild_id,
            func.similarity(Case.name, user_input) >= similarity,
        )
        .limit(25)
    )
    result = await session.scalars(stmt)

    return result.all()


async def get_vip_statuses_by_input(
    session: AsyncSession, *, guild_id: int, user_input: str
) -> Sequence[VipStatus]:
    """Get the list of VIP-statuses for a guild by user input."""

    a = 0.7
    similarity = (len(user_input) / 100) ** a

    stmt = (
        select(VipStatus)
        .where(
            VipStatus.guild_id == guild_id,
            func.similarity(VipStatus.name, user_input) >= similarity,
        )
        .limit(25)
    )
    result = await session.scalars(stmt)

    return result.all()


async def get_vip_status_by_id(
    session: AsyncSession,
    *,
    guild_id: int,
    vip_id: int,
    for_update: bool = False,
) -> VipStatus | None:
    """Get a VIP-status by id for a guild."""

    stmt = select(VipStatus).where(
        VipStatus.guild_id == guild_id, VipStatus.id == vip_id
    )
    if for_update:
        stmt = stmt.with_for_update()

    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def get_case_by_id(
    session: AsyncSession,
    *,
    guild_id: int,
    case_id: int,
    for_update: bool = False,
) -> Case | None:
    """Get a color by id for a guild."""
    stmt = select(Case).where(Case.guild_id == guild_id, Case.id == case_id)
    if for_update:
        stmt = stmt.with_for_update()

    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def get_battlepass_level(
    session: AsyncSession, *, guild_id: int, level: int
) -> BattlepassLevel | None:
    """Get a battlepass level by level num for a guild."""
    stmt = select(BattlepassLevel).where(
        BattlepassLevel.guild_id == guild_id, BattlepassLevel.level == level
    )

    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def get_guild_battlepass_levels(
    session: AsyncSession,
    *,
    guild_id: int,
) -> Sequence[BattlepassLevel]:
    """Get battlepass levels for a guild."""

    stmt = (
        select(BattlepassLevel)
        .where(BattlepassLevel.guild_id == guild_id)
        .order_by(asc(BattlepassLevel.level))
    )
    result = await session.execute(stmt)

    return result.scalars().all()


async def get_user_casino_bet_by_game_id(
    session: AsyncSession, *, user_id: int, game_id: int
) -> Any:
    """Get a user's casino bet by game ID."""
    stmt = select(CasinoBet).where(
        CasinoBet.user_id == user_id,
        CasinoBet.game_id == game_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_expired_casino_game_ids(
    session: AsyncSession, *, dt: datetime
) -> Sequence[int]:
    """Get ids of pending casino games whose end time has passed."""
    stmt = select(CasinoGame.id).where(
        CasinoGame.state == CasinoGameStateEnum.PENDING,
        CasinoGame.end_time <= dt,
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_expired_casino_game_for_update(
    session: AsyncSession, *, game_id: int, dt: datetime
) -> CasinoGame | None:
    """Lock a pending casino game with expired end time, with bets and users.

    Returns None if the game is already finished, was extended, or is
    currently locked by another transaction (join/leave in progress).
    """
    stmt = (
        select(CasinoGame)
        .where(
            CasinoGame.id == game_id,
            CasinoGame.state == CasinoGameStateEnum.PENDING,
            CasinoGame.end_time <= dt,
        )
        .options(selectinload(CasinoGame.bets).selectinload(CasinoBet.user))
        .with_for_update(of=CasinoGame, skip_locked=True)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_or_create_processed_thread(
    session: AsyncSession, *, thread_id: int
) -> ProcessedForumThread | None:
    """Create processed forum thread in the database."""

    stmt = select(ProcessedForumThread).where(
        ProcessedForumThread.thread_id == thread_id
    )

    result = await session.execute(stmt)

    processed_thread = result.scalar_one_or_none()

    if processed_thread is None:
        new_processed_thread = ProcessedForumThread(thread_id=thread_id)
        session.add(new_processed_thread)

    return processed_thread


async def reset_users_voice_activity(session: AsyncSession) -> int:
    """Reset temp voice activity for all users and update their total voice activity accordingly. Returns the count of affected users."""  # noqa: E501
    now = datetime.now(UTC)

    stmt = (
        update(User)
        .where(User.temp_voice_activity.is_not(None))
        .values(
            voice_activity=User.voice_activity
            + func.floor(
                extract("epoch", literal(now))
                - extract("epoch", User.temp_voice_activity)
            ),
            temp_voice_activity=None,
        )
    )

    result = await session.execute(stmt)

    return result.rowcount or 0  # type: ignore


async def get_clan_shop_item_by_name(
    session: AsyncSession, *, guild_id: int, name: str
) -> GuildClanShopItem | None:
    """Get a clan shop item by name for a guild."""

    stmt = select(GuildClanShopItem).where(
        GuildClanShopItem.guild_id == guild_id, GuildClanShopItem.name == name
    )

    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def get_economy_shop_item_by_name(
    session: AsyncSession, *, guild_id: int, name: str
) -> GuildEconomyShopItem | None:
    """Get an economy shop item by name for a guild."""

    stmt = select(GuildEconomyShopItem).where(
        GuildEconomyShopItem.guild_id == guild_id,
        GuildEconomyShopItem.name == name,
    )

    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def get_organization_roles_ids(
    session: AsyncSession, *, guild_id: int
) -> Sequence[int]:
    """Get the list of organizational role ids for a guild."""

    stmt = select(GuildOrganizationalRole.role_id).where(
        GuildOrganizationalRole.guild_id == guild_id
    )

    result = await session.execute(stmt)

    return result.scalars().all()


async def get_organization_role_by_role_id(
    session: AsyncSession, *, guild_id: int, role_id: int
) -> GuildOrganizationalRole | None:
    """Get an organizational role by its role id for a guild."""

    stmt = select(GuildOrganizationalRole).where(
        GuildOrganizationalRole.guild_id == guild_id,
        GuildOrganizationalRole.role_id == role_id,
    )

    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def get_forum_guilds(
    session: AsyncSession,
) -> Sequence[GuildForumConfig]:
    """Get all forum configurations."""

    stmt = select(GuildForumConfig)

    result = await session.execute(stmt)

    return result.scalars().all()


async def get_guild_forum_config(
    session: AsyncSession, *, guild_id: int
) -> GuildForumConfig | None:
    """Get the forum configuration for a guild."""

    stmt = select(GuildForumConfig).where(
        GuildForumConfig.guild_id == guild_id
    )

    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def get_active_forum_guilds(
    session: AsyncSession,
) -> Sequence[GuildForumConfig]:
    """Get all forum configurations."""

    stmt = select(GuildForumConfig).where(
        GuildForumConfig.notify_webhook != None,  # noqa: E711
        GuildForumConfig.section_id != None,  # noqa: E711
    )

    result = await session.execute(stmt)

    return result.scalars().all()


async def get_guild_level(
    session: AsyncSession, guild_id: int, level: int
) -> GuildLevel | None:
    """Get the closest configured guild level not exceeding the given level."""

    stmt = (
        select(GuildLevel)
        .where(GuildLevel.guild_id == guild_id, GuildLevel.level <= level)
        .order_by(GuildLevel.level.desc())
        .limit(1)
    )

    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def get_guild_level_role_ids(
    session: AsyncSession, guild_id: int
) -> Sequence[int]:
    """Get the distinct role ids of configured guild levels for a guild."""

    stmt = (
        select(GuildLevel.role_id)
        .where(GuildLevel.guild_id == guild_id)
        .distinct()
    )

    result = await session.execute(stmt)

    return result.scalars().all()


async def insert_moderation_message(
    session: AsyncSession, *, message: ModerationMessage
) -> ModerationMessage:
    """Delete expired moderation messages and insert a new one."""

    expired_ids = (
        select(ModerationMessage.id)
        .where(
            ModerationMessage.time_now
            <= datetime.now(UTC) - timedelta(days=60)
        )
        .order_by(ModerationMessage.time_now)
        .limit(100)
        .with_for_update(skip_locked=True)
    )
    stmt = delete(ModerationMessage).where(
        ModerationMessage.id.in_(expired_ids)
    )

    await session.execute(stmt)

    session.add(message)

    return message


async def get_guild_subscription(
    session: AsyncSession, *, guild_id: int
) -> DiscordGuild | None:
    """Get guild subscription."""
    stmt = select(DiscordGuild).where(DiscordGuild.guild_id == guild_id)

    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def get_badges(
    session: AsyncSession,
    *,
    guild_id: int,
    badge_type: BadgeTypeEnum = BadgeTypeEnum.ALL,
    for_update: bool = False,
) -> tuple[Sequence[GlobalBadge], Sequence[GuildBadge]]:
    """Get badges based on type.

    Returns:
        (global_badges, guild_badges)
    """
    global_badges: Sequence[GlobalBadge] = []
    guild_badges: Sequence[GuildBadge] = []

    if badge_type in (BadgeTypeEnum.GLOBAL, BadgeTypeEnum.ALL):
        stmt = select(GlobalBadge)

        if for_update:
            stmt.with_for_update()

        result = await session.execute(stmt)
        global_badges = result.scalars().all()

    if badge_type in (BadgeTypeEnum.LOCAL, BadgeTypeEnum.ALL):
        stmt = select(GuildBadge).where(GuildBadge.guild_id == guild_id)

        if for_update:
            stmt.with_for_update()

        result = await session.execute(stmt)
        guild_badges = result.scalars().all()

    return global_badges, guild_badges


async def get_badges_by_user_input_and_type(
    session: AsyncSession,
    *,
    badge_type: BadgeTypeEnum,
    guild_id: int,
    user_input: str,
) -> Sequence[GuildBadge | GlobalBadge]:
    """Get the list of guild/global badges  by user input."""
    a = 0.7
    similarity = (len(user_input) / 100) ** a

    model = GlobalBadge

    where_clauses = [
        func.similarity(model.name, user_input) >= similarity,
    ]
    if badge_type == BadgeTypeEnum.LOCAL:
        model = GuildBadge
        where_clauses.append(model.guild_id == guild_id)  # type: ignore

    stmt = select(model).limit(25)
    stmt.where(*where_clauses)

    result = await session.scalars(stmt)

    return result.all()


async def get_badge_by_id(
    session: AsyncSession,
    *,
    badge_type: BadgeTypeEnum,
    badge_id: int,
    guild_id: int,
) -> GuildBadge | GlobalBadge | None:
    """Get a VIP-status by id for a guild."""

    model = GlobalBadge

    where_clauses = [model.id == badge_id]
    if badge_type == BadgeTypeEnum.LOCAL:
        model = GuildBadge
        where_clauses.append(model.guild_id == guild_id)  # type: ignore

    stmt = select(model).limit(25)
    stmt.where(*where_clauses)

    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def get_user_badges_for_update(
    session: AsyncSession,
    *,
    badge_type: BadgeTypeEnum = BadgeTypeEnum.ALL,
    user_id: int,
    guild_id: int,
    for_update: bool = False,
) -> tuple[Sequence[UserGlobalBadge], Sequence[UserGuildBadge]]:
    """Get user badges based on type.

    Returns:
        global_badges: Sequence of UserGlobalBadge
        guild_badges: Sequence of UserGuildBadge
    """

    global_badges: Sequence[UserGlobalBadge] = []
    guild_badges: Sequence[UserGuildBadge] = []

    if badge_type in (BadgeTypeEnum.GLOBAL, BadgeTypeEnum.ALL):
        stmt = (
            select(UserGlobalBadge)
            .where(UserGlobalBadge.user_id == user_id)
            .options(joinedload(UserGlobalBadge.badge))
        )

        if for_update:
            stmt.with_for_update()

        result = await session.scalars(stmt)
        global_badges = result.all()

    if badge_type in (BadgeTypeEnum.LOCAL, BadgeTypeEnum.ALL):
        stmt = (
            select(UserGuildBadge)
            .where(
                UserGuildBadge.guild_id == guild_id,
                UserGuildBadge.user_id == user_id,
            )
            .options(joinedload(UserGuildBadge.badge))
        )

        if for_update:
            stmt.with_for_update()

        result = await session.scalars(stmt)
        guild_badges = result.all()

    return global_badges, guild_badges
