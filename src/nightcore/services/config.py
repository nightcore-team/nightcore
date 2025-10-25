"""Service for managing guild configurations in the Nightcore application."""

from typing import TYPE_CHECKING
from contextlib import asynccontextmanager
from src.infra.db.operations import GuildT, get_specified_guild_config

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.exceptions import (
    ConfigMissingButCreatingError,
    ConfigMissingError,
)


@asynccontextmanager
async def specified_guild_config(
    bot: "Nightcore",
    guild_id: int,
    config_type: type[GuildT],
    _create: bool = True,
):
    """Open a context manager for the guild configuration."""
    async with bot.uow.start() as session:
        guild_config: GuildT | None = await get_specified_guild_config(
            session,
            config_type=config_type,
            guild_id=guild_id,
        )
        if not guild_config:
            if _create:
                session.add(config_type(guild_id=guild_id))  # type: ignore
                await session.commit()  # type: ignore
                raise ConfigMissingButCreatingError(guild_id)
            raise ConfigMissingError(guild_id)
        yield guild_config, session
