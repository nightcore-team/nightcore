"""Unit of Work (UoW) implementation for managing database sessions."""

import logging
import time
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


class UnitOfWork:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]):
        self._sm = sessionmaker

    @asynccontextmanager
    async def start(self):
        """Start a new db session."""
        async with self._sm() as session:
            start_time = time.perf_counter()
            logger.info("[UoW] Session started")

            try:
                yield session
                commit_start = time.perf_counter()
                await session.commit()
                logger.info(
                    f"[UoW] Commit finished in {time.perf_counter() - commit_start:.10f}s "  # noqa: E501
                    f"(total {time.perf_counter() - start_time:.10f}s)"
                )
            except Exception as e:
                logger.warning(
                    f"[UoW] Exception occurred: {e!r}, rolling back..."
                )
                rollback_start = time.perf_counter()
                await session.rollback()
                logger.info(
                    f"[UoW] Rollback finished in {time.perf_counter() - rollback_start:.10f}s "  # noqa: E501
                    f"(total {time.perf_counter() - start_time:.10f}s)"
                )
                raise
            finally:
                logger.info(
                    f"[UoW] Session closed (total time {time.perf_counter() - start_time:.10f}s)"  # noqa: E501
                )
