"""Main entry point for the Nightcore bot."""

import asyncio
import signal

from src.config.config import config
from src.infra.db.session import get_async_sessionmaker
from src.infra.db.uow import UnitOfWork
from src.nightcore.api.setup import create_api_server
from src.nightcore.setup import create_bot
from src.utils.logging.setup import setup_logging, stop_logging


async def main() -> None:
    """Main function to start the Nightcore bot."""
    logger = setup_logging()
    uow = UnitOfWork(get_async_sessionmaker(config.db.ENGINE))  # type: ignore

    bot = create_bot(
        uow=uow,
    )
    bot_task = asyncio.create_task(bot.startup())

    server = create_api_server(bot)
    server_task = asyncio.create_task(server.serve())

    loop = asyncio.get_running_loop()

    def shutdown() -> None:
        logger.info("Shutdown signal received. Stopping Nightcore bot...")
        bot_task.cancel()
        server_task.cancel()

    loop.add_signal_handler(
        signal.SIGTERM,
        shutdown,
    )
    loop.add_signal_handler(signal.SIGINT, shutdown)

    logger.info("Starting Nightcore bot...")
    logger.info("Starting API server...")
    try:
        _, pending = await asyncio.wait(
            [bot_task, server_task], return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()

        await asyncio.gather(*pending, return_exceptions=True)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error("Error occurred: %s", e)
    finally:
        if not bot_task.done():
            bot_task.cancel()
        if not server_task.done():
            server_task.cancel()
        await asyncio.gather(bot_task, server_task, return_exceptions=True)
        logger.info("Nightcore bot has been stopped.")
        stop_logging()


if __name__ == "__main__":
    asyncio.run(main())
