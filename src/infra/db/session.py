"""Session factory for creating SQLAlchemy async sessions."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)


def get_async_sessionmaker(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """
    Get an async sessionmaker for the given engine.

    Attributes:
        engine: The async engine to bind the sessionmaker to.
        bind: The engine to bind the sessionmaker to.
        expire_on_commit: Whether to expire objects on commit (default: False).
        class_: The session class to use (default: AsyncSession).
        close_resets_only: Whether to reset the session on close instead of closing it (default: False).

    Returns:
        An async sessionmaker instance.

    """  # noqa: E501

    return async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
        close_resets_only=True,
    )
