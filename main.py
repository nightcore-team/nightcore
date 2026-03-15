"""Main entry point for the Nightcore bot."""

import asyncio
import signal

from src.config.config import config
from src.infra.db.session import get_async_sessionmaker
from src.infra.db.uow import UnitOfWork
from src.infra.redis.client import create_redis_client
from src.infra.redis.repository import GuildStateRepository
from src.nightcore.setup import create_bot
from src.utils.logging.setup import setup_logging, stop_logging


async def main() -> None:
    """Main function to start the Nightcore bot."""
    logger = setup_logging()
    uow = UnitOfWork(get_async_sessionmaker(config.db.ENGINE))  # type: ignore
    guild_state_repository = GuildStateRepository(create_redis_client())
    await guild_state_repository.connect()
    await guild_state_repository.mark_not_ready()

    bot = create_bot(
        uow=uow,
        guild_state_repository=guild_state_repository,
    )
    bot_task = asyncio.create_task(bot.startup())

    loop = asyncio.get_running_loop()

    def shutdown() -> None:
        logger.info("Shutdown signal received. Stopping Nightcore bot...")
        bot_task.cancel()

    loop.add_signal_handler(
        signal.SIGTERM,
        shutdown,
    )
    loop.add_signal_handler(signal.SIGINT, shutdown)

    logger.info("Starting Nightcore bot...")
    logger.info("Starting API server...")
    try:
        await bot_task
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error("Error occurred: %s", e)
    finally:
        if not bot_task.done():
            bot_task.cancel()
        await asyncio.gather(bot_task, return_exceptions=True)
        await guild_state_repository.mark_not_ready()
        await guild_state_repository.close()
        logger.info("Nightcore bot has been stopped.")
        stop_logging()


if __name__ == "__main__":
    asyncio.run(main())
