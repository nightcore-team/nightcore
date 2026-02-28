"""Main entry point for the Nightcore bot."""

import asyncio
import signal

from src.config.config import config
from src.infra.db.session import get_async_sessionmaker
from src.infra.db.uow import UnitOfWork
from src.nightcore.setup import create_bot
from src.utils.logging.setup import setup_logging, stop_logging


async def main() -> None:
    """Main function to start the Nightcore bot."""
    logger = setup_logging()
    uow = UnitOfWork(get_async_sessionmaker(config.db.ENGINE))  # type: ignore
    bot = create_bot(uow=uow)

    bot_task = asyncio.create_task(bot.startup())

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(
        signal.SIGTERM,
        lambda: bot_task.cancel(),
    )

    logger.info("Starting Nightcore bot...")
    try:
        await bot_task
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error("Error occurred: %s", e)
    finally:
        logger.info("Nightcore bot has been stopped.")
        stop_logging()


if __name__ == "__main__":
    asyncio.run(main())
