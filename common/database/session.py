from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from common.config import settings

logger = logging.getLogger(__name__)


class DatabaseSessionManager:
    """Manages SQLAlchemy 2.0 AsyncEngine and async session factory."""

    def __init__(self, db_url: str | None = None) -> None:
        self._url: str = db_url or settings.DATABASE_URL
        self._engine: AsyncEngine | None = None
        self._sessionmaker: async_sessionmaker[AsyncSession] | None = None

    def init(self) -> None:
        """Initialize async engine and sessionmaker."""
        if self._engine is not None:
            return

        self._engine = create_async_engine(
            self._url,
            echo=(settings.ENVIRONMENT == "development"),
            future=True,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        self._sessionmaker = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        logger.info("Database engine and sessionmaker initialized.")

    async def close(self) -> None:
        """Dispose of the database engine."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None
            logger.info("Database connection pool disposed.")

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._sessionmaker is None:
            self.init()
        assert self._sessionmaker is not None
        return self._sessionmaker

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Provide a transactional async session."""
        session: AsyncSession = self.session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def ping(self) -> bool:
        """Readiness check: verifies Postgres responds to SELECT 1."""
        if self._engine is None:
            self.init()
        assert self._engine is not None
        try:
            async with self._engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.warning(f"Database readiness ping failed: {e}")
            return False


db_manager = DatabaseSessionManager()


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Dependency injector for FastAPI endpoints."""
    async with db_manager.session() as session:
        yield session
