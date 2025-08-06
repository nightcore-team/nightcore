"""Main entry point for the Nightcore bot."""

from logging import Logger

from src.config.config import config
from src.nightcore.bot import Nightcore
from src.nightcore.setup import create_bot
from src.utils.logging.setup import setup_logging


async def main() -> None:
    """Main function to start the Nightcore bot."""
    logger: Logger = setup_logging()
    bot: Nightcore = await create_bot()

    logger.info("Starting Nightcore bot...")

    try:
        async with bot:
            await bot.start(token=config.bot.BOT_TOKEN)
    except Exception as e:
        logger.error(f"Error occurred: {e}")
    finally:
        await bot.close()
        if not bot.is_closed():
            logger.info("Nightcore bot has been stopped.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
