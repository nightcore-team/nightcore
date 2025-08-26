"""Unit of Work (UoW) implementation for managing database sessions."""

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class UnitOfWork:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]):
        self._sm = sessionmaker

    @asynccontextmanager
    async def start(self):
        async with self._sm() as session:
            try:
                yield session
                await session.commit()
            except:
                await session.rollback()
                raise
