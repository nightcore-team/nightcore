"""Unit of Work (UoW) implementation for managing database sessions."""

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.session import SessionFactory


class UnitOfWork:
    def __init__(self, session_factory: SessionFactory):
        self._session_factory = session_factory
        self.session: AsyncSession | None = None

    @asynccontextmanager
    async def start(self):
        """Start a unit of work with a new session."""
        self.session = self._session_factory.create_session()
        try:
            yield self
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        finally:
            await self.session.close()
            self.session = None
