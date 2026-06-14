"""Service for managing guild configurations in the Nightcore application."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from src.infra.db.operations import GuildT, get_specified_guild_config

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


@asynccontextmanager
async def specified_guild_config(
    bot: Nightcore,
    guild_id: int,
    config_type: type[GuildT],
):
    """Open a context manager for the guild configuration."""

    async with bot.uow.start() as session:
        guild_config: GuildT = await get_specified_guild_config(
            session,
            config_type=config_type,
            guild_id=guild_id,
        )

        yield guild_config, session
