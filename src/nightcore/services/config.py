"""Service for managing guild configurations in the Nightcore application."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.operations import (
    GuildT,
    get_specified_guild_config,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


@asynccontextmanager
async def specified_guild_config(
    bot: Nightcore,
    guild_id: int,
    config_type: type[GuildT],
    *,
    for_update: bool = False,
    readonly: bool = False,
) -> AsyncGenerator[tuple[GuildT, AsyncSession]]:
    """Open a context manager for the guild configuration."""

    # for_update implies a write transaction; override readonly
    effective_readonly = readonly and not for_update

    # pure reads should use readonly to allow DB replica routing
    # and to force rollback instead of commit
    async with bot.uow.start(readonly=effective_readonly) as session:
        guild_config = await get_specified_guild_config(
            session,
            config_type=config_type,
            guild_id=guild_id,
            for_update=for_update,
        )

        yield guild_config, session
