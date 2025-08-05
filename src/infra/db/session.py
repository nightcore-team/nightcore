"""Session factory for creating SQLAlchemy async sessions."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)


class SessionFactory:
    def __init__(self, engine: AsyncEngine):
        self.engine = engine
        self._sessionmaker = async_sessionmaker(
            self.engine, expire_on_commit=False
        )

    def create_session(self) -> AsyncSession:
        """Create a new AsyncSession."""
        return self._sessionmaker()
