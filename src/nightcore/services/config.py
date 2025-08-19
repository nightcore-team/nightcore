"""Service for managing guild configurations in the Nightcore application."""

from contextlib import asynccontextmanager

from src.infra.db.operations import T, get_specified_guild_config
from src.nightcore.bot import Nightcore
from src.nightcore.exceptions import ConfigMissingError


@asynccontextmanager
async def specified_guild_config(
    bot: Nightcore,
    guild_id: int,
    config_type: type[T],
):
    """Open a context manager for the guild configuration."""
    async with bot.uow.start() as uow:
        guild_config: T | None = await get_specified_guild_config(
            uow.session,  # type: ignore
            config_type=config_type,
            guild_id=guild_id,
        )
        if not guild_config:
            uow.session.add(config_type(guild_id=guild_id))  # type: ignore
            await uow.session.commit()  # type: ignore
            raise ConfigMissingError(guild_id)
        yield guild_config
