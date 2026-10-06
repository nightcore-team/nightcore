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

    bot = create_bot(uow=uow)
    server = create_api_server(bot)

    bot_task = asyncio.create_task(bot.startup(), name="bot")
    server_task = asyncio.create_task(server.serve(), name="api")
    tasks = {bot_task, server_task}

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def request_shutdown() -> None:
        logger.info("Shutdown signal received")
        server.should_exit = True
        bot_task.cancel()
        stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, request_shutdown)

    try:
        done, pending = await asyncio.wait(
            tasks, return_when=asyncio.FIRST_COMPLETED
        )

        for t in done:
            if t.cancelled():
                logger.warning("Task %s was cancelled", t.get_name())
            elif (exc := t.exception()) is not None:
                logger.error("Task %s crashed", t.get_name(), exc_info=exc)
            else:
                logger.warning(
                    "Task %s finished unexpectedly (no error)", t.get_name()
                )

        server.should_exit = True
        for t in pending:
            if t is not server_task:
                t.cancel()

        await asyncio.gather(*pending, return_exceptions=True)
    finally:
        logger.info("Nightcore bot has been stopped.")
        stop_logging()


if __name__ == "__main__":
    asyncio.run(main())
