"""The module contains database operations for the Nightcore bot."""

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from typing import Any, TypeVar, cast

from async_lru import alru_cache
from sqlalchemy import exists, extract, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config.config import config
from src.infra.cache.async_lru import alru_invalidator
from src.infra.db.models import (
    ChangeStat,
    Clan,
    ClanMember,
    GuildClansConfig,
    GuildEconomyConfig,
    GuildInfomakerConfig,
    GuildLevelsConfig,
    GuildLoggingConfig,
    GuildModerationConfig,
    GuildNotificationsConfig,
    GuildPrivateChannelsConfig,
    GuildTicketsConfig,
    MainGuildConfig,
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
)
from src.infra.db.models._annot import (
    ModerationStatsResultAnnot,
    OrgRoleWithoutTagAnnot,
    Rules,
)
from src.infra.db.models._enums import (
    ChannelType,
    ClanMemberRoleEnum,
    MultiplierTypeEnum,
    NotifyStateEnum,
    RoleRequestStateEnum,
    TicketStateEnum,
)
from src.infra.db.utils import (
    build_base_filters as _build_base_moderstats_filters,
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
    MainGuildConfig,
    GuildInfomakerConfig,
)


async def get_specified_guild_config(
    session: AsyncSession, *, config_type: type[GuildT], guild_id: int
) -> GuildT | None:
    """Get the guild configuration from the database."""
    stmt = select(config_type).where(config_type.guild_id == guild_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_guild_rules(
    session: AsyncSession, *, guild_id: int
) -> Rules | None:
    """Get the guild rules from the database."""
    stmt = select(MainGuildConfig.guild_rules).where(
        MainGuildConfig.guild_id == guild_id
    )
    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def get_specified_channel(
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


async def get_specified_field(
    session: AsyncSession,
    *,
    guild_id: int,
    config_type: type[GuildT],
    field_name: str,
) -> Any:
    """Get the specified field from the database."""
    column = getattr(config_type, field_name)
    stmt = select(column).where(config_type.guild_id == guild_id)
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
) -> Sequence[NotifyState]:
    """Get all pending notifications."""
    stmt = select(NotifyState).where(
        NotifyState.state == NotifyStateEnum.PENDING
    )
    result = await session.scalars(stmt)
    return result.all()


async def get_shop_order_state(
    session: AsyncSession, *, guild_id: int, custom_id: str
) -> ShopOrderState | None:
    """Get the shop order state from the database."""
    stmt = (
        select(ShopOrderState)
        .where(
            ShopOrderState.guild_id == guild_id,
            ShopOrderState.custom_id == custom_id,
        )
        .with_for_update()
    )
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


# TODO: rewrite to use all models (like in get_specified_guild_config)
async def get_or_create_user(
    session: AsyncSession, *, guild_id: int, user_id: int
) -> tuple[User, bool]:
    """Get or create a user in the database."""
    stmt = (
        insert(User)
        .values(guild_id=guild_id, user_id=user_id)
        .on_conflict_do_nothing(constraint="ux_user_guild_user")
        .returning(User.user_id)
    )
    res = await session.execute(stmt)
    created = res.scalar_one_or_none() is not None

    user = await session.scalar(
        select(User).where(User.guild_id == guild_id, User.user_id == user_id)
    )
    return user, created  # type: ignore


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
    alru_invalidator(get_user_infractions, guild_id=guild_id, user_id=user_id)
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


async def get_clans_by_spec(
    session: AsyncSession,
    *,
    guild_id: int,
    spec: str | None = None,
) -> Sequence[Clan]:
    """Get clans for a guild ordered by the specified spec (e.g., 'reputation' or 'members')."""  # noqa: E501
    stmt = select(Clan).where(Clan.guild_id == guild_id).limit(10)

    match spec:
        case "members":
            stmt = (
                select(Clan)
                .join(Clan.members)
                .where(Clan.guild_id == guild_id)
                .group_by(Clan.id)
                .order_by(func.count(ClanMember.id).desc())
                .limit(10)
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
) -> ClanMember | None:
    """Get the clan member configuration from the database."""
    stmt = select(ClanMember).where(
        ClanMember.guild_id == guild_id, ClanMember.user_id == user_id
    )
    if with_relations:
        stmt = stmt.options(
            selectinload(ClanMember.clan).selectinload(Clan.deputies)
        )
    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def get_clan_by_id(
    session: AsyncSession,
    *,
    guild_id: int,
    clan_id: int | None = None,
) -> Clan | None:
    """Get clan by id."""
    stmt = select(Clan).where(Clan.guild_id == guild_id)
    if clan_id:
        stmt = stmt.where(Clan.id == clan_id)

    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def get_clan_by_name(
    session: AsyncSession, *, guild_id: int, clan_name: str
) -> Clan | None:
    """Get the clan configuration from the database."""

    stmt = select(Clan).where(
        Clan.guild_id == guild_id, Clan.name == clan_name
    )
    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def get_private_room_state(
    session: AsyncSession, *, user_id: int
) -> PrivateRoomState | None:
    """Get the private room state for a user."""
    stmt = (
        select(PrivateRoomState)
        .where(PrivateRoomState.user_id == user_id)
        .limit(1)
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def create_temp_punish(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
    category: str,
    end_time: datetime,
) -> TempPunish:
    """Create a new temporary punishment entry in the database."""
    temp_punish = TempPunish(
        guild_id=guild_id,
        user_id=user_id,
        category=category,
        end_time=end_time,
    )
    session.add(temp_punish)
    return temp_punish


async def get_temp_infractions(session: AsyncSession) -> Sequence[TempPunish]:
    """Get the list of temporary punishments from the database."""
    stmt = select(TempPunish)
    result = await session.scalars(stmt)
    return result.all()


async def get_latest_temp_punish(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
    category: str,
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
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def get_user_notify_by_end_time(
    session: AsyncSession, *, guild_id: int, user_id: int, ts: int
) -> NotifyState | None:
    """Get the notify state for a user in a guild by end time."""
    stmt = (
        select(NotifyState)
        .where(
            NotifyState.guild_id == guild_id,
            NotifyState.user_id == user_id,
            func.floor(extract("epoch", NotifyState.end_time)) == ts,
            NotifyState.state == NotifyStateEnum.PENDING,
        )
        .limit(1)
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def get_latest_user_ticket(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
) -> TicketState | None:
    """Get the latest ticket state for a user in a guild."""
    stmt = (
        select(TicketState)
        .where(
            TicketState.guild_id == guild_id,
            TicketState.author_id == user_id,
        )
        .order_by(
            TicketState.updated_at.desc().nulls_last(),
        )
        .limit(1)
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def get_latest_user_role_request(
    session: AsyncSession,
    *,
    guild_id: int | None,
    user_id: int,
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
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def get_fraction_roles(
    session: AsyncSession, *, guild_id: int
) -> list[str]:
    """Get the list of fraction roles for a guild."""

    stmt = select(GuildModerationConfig.fraction_roles_access_roles_ids).where(
        GuildModerationConfig.guild_id == guild_id
    )
    roles = await session.execute(stmt)

    result = roles.scalar_one_or_none()

    return list(result.keys()) if result else []


@alru_cache()
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
            TicketState.state == TicketStateEnum.CLOSED,
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

    result = await session.execute(stmt)
    messages_data = dict(result.all())  # type: ignore

    return {
        "moderators": moderators,
        "punishments": punishments,
        "tickets": tickets,
        "role_requests": role_requests,
        "changestats": changestats,
        "messages": messages_data,  # type: ignore
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
        .where(
            User.guild_id == guild_id,
            User.battle_pass_level != 1,
            User.battle_pass_points != 0,
        )
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
    boundary = datetime.now(timezone.utc) - timedelta(days=7)

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
    boundary = datetime.now(timezone.utc) - timedelta(
        hours=config.bot.ROLE_REQUESTS_ALIVE_HOURS
    )

    stmt = select(RoleRequestState).where(
        RoleRequestState.state.in_(
            [
                "pending",
            ]
        ),
        RoleRequestState.updated_at <= boundary,
    )

    result = await session.scalars(stmt)
    return result.all()


async def get_all_closed_tickets(
    session: AsyncSession,
) -> Sequence[TicketState]:
    """Get all closed tickets."""
    stmt = select(TicketState).where(
        TicketState.state == TicketStateEnum.CLOSED
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_all_temp_roles(
    session: AsyncSession,
) -> Sequence[TempRole]:
    """Get all temporary roles."""
    stmt = select(TempRole)
    result = await session.scalars(stmt)

    return result.all()


async def get_total_users_count(session: AsyncSession) -> int:
    """Get the total number of users in the database."""
    stmt = select(func.count()).select_from(User)

    return cast(int, await session.scalar(stmt))


async def get_organization_roles_full_json(
    session: AsyncSession, *, guild_id: int
) -> dict[str, OrgRoleWithoutTagAnnot] | None:
    """Get the list of organization roles for a guild."""
    stmt = select(MainGuildConfig.organizational_roles).where(
        MainGuildConfig.guild_id == guild_id
    )
    result = await session.execute(stmt)
    return cast(
        dict[str, OrgRoleWithoutTagAnnot] | None, result.scalar_one_or_none()
    )


async def get_illegal_roles_full_json(
    session: AsyncSession, *, guild_id: int
) -> dict[str, OrgRoleWithoutTagAnnot] | None:
    """Get the list of organization roles for a guild."""
    stmt = select(MainGuildConfig.illegal_roles).where(
        MainGuildConfig.guild_id == guild_id
    )
    result = await session.execute(stmt)
    return cast(
        dict[str, OrgRoleWithoutTagAnnot] | None, result.scalar_one_or_none()
    )


async def get_organization_roles_ids(
    session: AsyncSession, *, guild_id: int
) -> list[int]:
    """Get the list of organization and illegal roles IDs for a guild."""
    stmt = (
        select(
            MainGuildConfig.organizational_roles, MainGuildConfig.illegal_roles
        )
        .where(MainGuildConfig.guild_id == guild_id)
        .limit(1)
    )

    row = (await session.execute(stmt)).one_or_none()
    if not row:
        return []

    organizational_roles, illegal_roles = row

    ids: list[int] = []
    for roles in (organizational_roles, illegal_roles):
        if roles:
            for value in roles.values():
                role_id = value.get("role_id")
                if role_id is not None:
                    ids.append(role_id)

    # Preserve original order while removing duplicates
    seen: set[int] = set()
    unique_ids: list[int] = []
    for r in ids:
        if r not in seen:
            seen.add(r)
            unique_ids.append(r)

    return unique_ids


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
    return result.scalar_one_or_none()


async def get_or_create_temp_multiplier(
    session: AsyncSession,
    *,
    guild_id: int,
    multiplier_type: MultiplierTypeEnum,
    multiplier: int = 1,
    duration: int = 3600,  # 1 година в секундах
) -> tuple[TempEconomyMultiplier, bool]:
    """Get or create a temporary economy multiplier for a guild."""

    stmt = (
        insert(TempEconomyMultiplier)
        .values(
            guild_id=guild_id,
            multiplier_type=multiplier_type,
            multiplier=multiplier,
            duration=duration,
            end_time=datetime.now(timezone.utc) + timedelta(seconds=duration),
        )
        .on_conflict_do_nothing(constraint="ux_temp_multiplier_guild_type")
        .returning(TempEconomyMultiplier.id)
    )
    res = await session.execute(stmt)
    created = res.scalar_one_or_none() is not None

    entity = await session.scalar(
        select(TempEconomyMultiplier).where(
            TempEconomyMultiplier.guild_id == guild_id,
            TempEconomyMultiplier.multiplier_type == multiplier_type,
        )
    )

    return entity, created  # type: ignore


async def get_all_expired_temp_multipliers(
    session: AsyncSession,
) -> Sequence[TempEconomyMultiplier]:
    """Get all expired temporary economy multipliers.

    Returns multipliers where end_time <= current time.
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)

    stmt = select(TempEconomyMultiplier).where(
        TempEconomyMultiplier.end_time <= now
    )
    result = await session.execute(stmt)
    return result.scalars().all()
