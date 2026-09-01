"""Unit of Work implementation for managing database sessions."""

import asyncio
import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 0.1


def _is_serialization_failure(exc: Exception) -> bool:
    """Check whether exception is a Postgres serialization failure (40001)."""
    if isinstance(exc, DBAPIError):
        orig = exc.orig
        if orig is not None:
            if getattr(orig, "sqlstate", None) == "40001":
                return True
            name = orig.__class__.__name__
            if name == "SerializationFailure":
                return True
            msg = str(orig)
            if "40001" in msg or "SerializationFailure" in msg:
                return True
        # fallback on DBAPIError message itself
        if "40001" in str(exc) or "SerializationFailure" in str(exc):
            return True
    # also handle asyncpg directly without DBAPIError wrapping
    if exc.__class__.__name__ == "SerializationFailure":
        return True
    if getattr(exc, "sqlstate", None) == "40001":
        return True
    return False


class UnitOfWork:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]):
        self._sm = sessionmaker

    @asynccontextmanager
    async def start(
        self,
        *,
        readonly: bool = False,
        isolation_level: str | None = None,
    ) -> AsyncGenerator[AsyncSession]:
        """Start a new unit of work session."""

        async with self._sm() as session:
            start_time = time.perf_counter()
            logger.info(
                "[UoW] Session started%s",
                f" readonly={readonly}"
                if readonly
                else f" isolation={isolation_level}"
                if isolation_level
                else "",
            )

            if isolation_level is not None:
                allowed = {
                    "READ COMMITTED",
                    "REPEATABLE READ",
                    "SERIALIZABLE",
                    "READ UNCOMMITTED",
                }
                lvl = isolation_level.upper()
                if lvl not in allowed:
                    raise ValueError(
                        f"Invalid isolation_level: {isolation_level}"
                    )
                await session.execute(
                    text(f"SET TRANSACTION ISOLATION LEVEL {lvl}")
                )

            try:
                yield session
            except Exception as exc:
                logger.error(
                    "[UoW] Exception occurred, rolling back, error: %s",
                    exc,
                )
                try:
                    await session.rollback()
                except Exception as rb_exc:
                    logger.error(
                        "[UoW] Rollback failed after exception: %s",
                        rb_exc,
                    )
                raise
            else:
                commit_start = time.perf_counter()
                # commit / readonly-rollback with isolation and retry
                for attempt in range(_MAX_RETRIES):
                    try:
                        if readonly:
                            await session.rollback()
                            logger.info(
                                "[UoW] Rollback finished for readonly "
                                "in %.6fs (total %.6fs)",
                                time.perf_counter() - commit_start,
                                time.perf_counter() - start_time,
                            )
                        else:
                            await session.commit()
                            logger.info(
                                "[UoW] Commit finished in %.6fs "
                                "(total %.6fs)",
                                time.perf_counter() - commit_start,
                                time.perf_counter() - start_time,
                            )
                        break
                    except DBAPIError as db_exc:
                        if _is_serialization_failure(
                            db_exc
                        ) and attempt < _MAX_RETRIES - 1:
                            delay = _RETRY_BASE_DELAY * (2**attempt)
                            logger.warning(
                                "[UoW] SerializationFailure on commit, "
                                "retry %d/%d after %.3fs: %s",
                                attempt + 1,
                                _MAX_RETRIES,
                                delay,
                                db_exc,
                            )
                            try:
                                await session.rollback()
                            except Exception:
                                pass
                            await asyncio.sleep(delay)
                            # retry commit only if transaction still usable;
                            # for postgres, we need to restart; just continue
                            # to retry commit attempt
                            continue
                        logger.error(
                            "[UoW] Commit failed, rolling back: %s",
                            db_exc,
                        )
                        try:
                            await session.rollback()
                        except Exception as rb_exc:
                            logger.error(
                                "[UoW] Rollback after commit failure "
                                "failed: %s",
                                rb_exc,
                            )
                        raise
                    except Exception as commit_exc:
                        logger.error(
                            "[UoW] Commit failed, rolling back: %s",
                            commit_exc,
                        )
                        try:
                            await session.rollback()
                        except Exception as rb_exc:
                            logger.error(
                                "[UoW] Rollback after commit failure "
                                "failed: %s",
                                rb_exc,
                            )
                        raise
            finally:
                logger.info(
                    "[UoW] Session closed (total time %.10fs)",
                    time.perf_counter() - start_time,
                )
