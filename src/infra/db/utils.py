"""Utilities for database operations."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING, TypeVar

from sqlalchemy.sql.elements import (
    BooleanClauseList,
    ColumnElement,
)

from src.infra.db.models._annot import ModerationInfractionsDataAnnot

if TYPE_CHECKING:
    from src.infra.db.models import (
        ChangeStat,
        ModerationMessage,
        Punish,
        RoleRequestState,
        TicketState,
    )

T = TypeVar(
    "T",
    "ChangeStat",
    "ModerationMessage",
    "Punish",
    "RoleRequestState",
    "TicketState",
)


def build_base_filters(
    model: type[T],
    guild_id: int,
    moderator_ids: list[int],
    from_date: datetime,
    to_date: datetime,
    date_field: str = "time_now",
) -> list[ColumnElement[bool] | BooleanClauseList]:
    """Build common filters for moderation queries."""
    date_column = getattr(model, date_field)

    return [
        model.guild_id == guild_id,
        model.moderator_id.in_(moderator_ids),
        date_column >= from_date,
        date_column <= to_date,
    ]


def group_infractions_by_moderator(
    moderators: dict[int, str],
    punishments: Sequence[Punish],
    tickets: Sequence[TicketState],
    role_requests: Sequence[RoleRequestState],
    changestats: Sequence[ChangeStat],
    messages: dict[int, int] | None,
) -> dict[int, ModerationInfractionsDataAnnot]:
    """Group infractions by moderator_id."""

    grouped: dict[int, ModerationInfractionsDataAnnot] = {
        mod_id: ModerationInfractionsDataAnnot(
            nickname=mod_name,
            punishments=[],
            tickets=[],
            role_requests=[],
            changestats=[],
        )
        for mod_id, mod_name in moderators.items()
    }

    for p in punishments:
        if p.moderator_id in grouped:
            grouped[p.moderator_id].punishments.append(p)

    for t in tickets:
        if t.moderator_id in grouped:
            grouped[t.moderator_id].tickets.append(t)

    for rr in role_requests:
        if rr.moderator_id in grouped:
            grouped[rr.moderator_id].role_requests.append(rr)

    for cs in changestats:
        if cs.moderator_id in grouped:
            grouped[cs.moderator_id].changestats.append(cs)

    if messages:
        for mod_id, msg_count in messages.items():
            if mod_id in grouped:
                grouped[mod_id].total_messages = msg_count

    return grouped
