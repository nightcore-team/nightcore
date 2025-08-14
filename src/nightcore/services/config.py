"""Service for managing guild configurations in the Nightcore application."""

from contextlib import asynccontextmanager

from src.infra.db.models.guild import GuildConfig
from src.infra.db.operations import get_guild_config
from src.nightcore.bot import Nightcore
from src.nightcore.exceptions import ConfigMissingError


@asynccontextmanager
async def open_guild_config(
    bot: Nightcore,
    guild_id: int,
):
    """Open a context manager for the guild configuration."""
    async with bot.uow.start() as uow:
        guild_config: GuildConfig | None = await get_guild_config(
            uow.session,  # type: ignore
            guild_id=guild_id,
        )
        if not guild_config:
            uow.session.add(GuildConfig(guild_id=guild_id))  # type: ignore
            await uow.session.commit()  # type: ignore
            raise ConfigMissingError(guild_id)
        yield guild_config
