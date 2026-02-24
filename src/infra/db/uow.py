"""Unit of Work (UoW) implementation for managing database sessions."""

import inspect
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CallSite:
    file: str
    line: int
    function: str

    def __str__(self) -> str:
        """Return a human-readable string representation of the call site."""
        return f"{self.file}:{self.line} in {self.function}()"


def find_callsite(*, skip_functions: set[str]) -> CallSite | None:
    """Find the call site in the stack that is not in the skip_functions set."""  # noqa: E501

    for frame_info in inspect.stack()[2:]:
        if frame_info.function in skip_functions:
            continue
        return CallSite(
            file=frame_info.filename,
            line=frame_info.lineno,
            function=frame_info.function,
        )

    return None


class UnitOfWork:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]):
        self._sm = sessionmaker

    @asynccontextmanager
    async def start(self, readonly: bool = False):
        """Start a new db session."""
        async with self._sm() as session:
            start_time = time.perf_counter()
            callsite = find_callsite(skip_functions={"start"})
            logger.info("[UoW] Session started callsite=%s", callsite)

            try:
                yield session

                commit_start = time.perf_counter()
                if not readonly:
                    await session.commit()
                else:
                    await session.rollback()
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
                    f"[UoW] Session closed callsite={find_callsite(skip_functions={'start'})} (total time {time.perf_counter() - start_time:.10f}s)"  # noqa: E501
                )
