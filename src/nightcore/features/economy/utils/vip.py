"""Utilities for granting VIP statuses."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from src.infra.db.models.user import UserVipStatus


def next_vip_expires_at(
    *,
    current: datetime | None,
    duration: int | None,
    now: datetime | None = None,
) -> datetime | None:
    """Resolve the new expiry of a VIP grant, extending the current one.

    `duration` is a number of seconds, None means the VIP is granted forever.
    A still valid VIP grows from its current expiry, an already expired one is
    restarted from now, so a grant never shortens a VIP and never resurrects
    one from a date in the past.
    """
    if duration is None:
        return None

    moment = now or datetime.now(UTC)
    base = current if current is not None and current > moment else moment

    return base + timedelta(seconds=duration)


def count_live_vip_statuses(
    statuses: Iterable[UserVipStatus],
    *,
    now: datetime | None = None,
) -> int:
    """Count the VIPs the user actually holds, skipping the expired ones.

    Expired rows are only cleared by the expiry task, so counting them would
    make the MAX_USER_VIPS quota shrink until the task happens to run.
    """
    moment = now or datetime.now(UTC)

    return sum(
        1
        for status in statuses
        if status.expires_at is None or status.expires_at > moment
    )


def format_duration(seconds: int) -> str:
    """Render a number of seconds as a compact duration, e.g. 7д or 1ч 30м."""
    if seconds <= 0:
        return "0с"

    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60

    if days:
        return f"{days}д" if not hours else f"{days}д {hours}ч"

    if hours:
        return f"{hours}ч" if not minutes else f"{hours}ч {minutes}м"

    if minutes:
        return f"{minutes}м"

    return f"{seconds}с"


def vip_reward_name(name: str, duration: int | None) -> str:
    """Build the displayed name of a VIP reward, with its expiry when set.

    A permanent VIP keeps the bare name, so only the temporary ones carry a
    hint and the lists stay readable.
    """
    if duration is None:
        return name

    return f"{name} ({format_duration(duration)})"
