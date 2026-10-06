"""Main entry point for the Nightcore bot."""

import asyncio
import signal

from src.config.config import config
from src.infra.db.session import get_async_sessionmaker
from src.infra.db.uow import UnitOfWork
from src.nightcore.api.setup import create_api_server
from src.nightcore.setup import create_bot
from src.utils.logging.setup import setup_logging, stop_logging

SHUTDOWN_TIMEOUT = 20.0


async def main() -> None:
    """Main function to start the Nightcore bot."""
    logger = setup_logging()
    loop = asyncio.get_running_loop()
    tasks: list[asyncio.Task[None]] = []

    try:
        uow = UnitOfWork(get_async_sessionmaker(config.db.ENGINE))  # type: ignore

        bot = create_bot(uow=uow)
        server = create_api_server(bot)

        bot_task = asyncio.create_task(bot.startup(), name="bot")
        server_task = asyncio.create_task(server.serve(), name="api")
        tasks = [bot_task, server_task]

        def request_shutdown() -> None:
            logger.info("Shutdown signal received")
            server.should_exit = True
            bot_task.cancel()

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, request_shutdown)

        logger.info("Starting Nightcore bot and API server...")

        done, _ = await asyncio.wait(
            tasks, return_when=asyncio.FIRST_COMPLETED
        )

        for t in done:
            if t.cancelled():
                logger.warning("Task %s was cancelled", t.get_name())
            elif (exc := t.exception()) is not None:
                logger.error("Task %s crashed", t.get_name(), exc_info=exc)
            else:
                logger.warning("Task %s finished (no error)", t.get_name())

    except Exception:
        logger.exception("Fatal error in main")
    finally:
        # --- Graceful shutdown ---
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.remove_signal_handler(sig)

        if tasks:
            server.should_exit = True  # type: ignore[possibly-undefined]
            for t in tasks:
                if t.get_name() == "bot":
                    t.cancel()

            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=SHUTDOWN_TIMEOUT,
                )
                for t, res in zip(tasks, results, strict=False):
                    if isinstance(res, Exception):
                        logger.error(
                            "Task %s failed during shutdown",
                            t.get_name(),
                            exc_info=res,
                        )
            except TimeoutError:
                logger.error(
                    "Shutdown timed out after %.0fs, tasks cancelled",
                    SHUTDOWN_TIMEOUT,
                )

        logger.info("Nightcore bot has been stopped.")
        stop_logging()


if __name__ == "__main__":
    asyncio.run(main())
