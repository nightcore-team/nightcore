"""Unit of Work implementation for managing database sessions."""

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


class UnitOfWork:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]):
        self._sm = sessionmaker

    @asynccontextmanager
    async def start(
        self,
        *,
        readonly: bool = False,
    ) -> AsyncIterator[AsyncSession]:
        """Start a new unit of work session."""

        async with self._sm() as session:
            start_time = time.perf_counter()
            logger.info(
                "[UoW] Session started",
            )

            try:
                yield session

                commit_start = time.perf_counter()
                if readonly:
                    await session.rollback()
                else:
                    await session.commit()

                logger.info(
                    "[UoW] Commit finished in %.6fs (total %.6fs)",
                    time.perf_counter() - commit_start,
                    time.perf_counter() - start_time,
                )
            except Exception as e:
                logger.error(
                    "[UoW] Exception occurred, rolling back, error: %s",
                    e,
                )
                await session.rollback()
                raise
            finally:
                logger.info(
                    "[UoW] Session closed (total time %.10fs)",
                    time.perf_counter() - start_time,
                )
