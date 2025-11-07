"""
Database manager for Character Agent Service.
"""

from typing import Dict, Optional

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

import sys
sys.path.append('../..')
from shared.logging_config import get_logger

from src.db.models import Base

logger = get_logger(__name__)


class DatabaseManager:
    """Manage database connections and sessions."""

    def __init__(self, config: Dict):
        self.config = config
        db_config = config.get("database", {})

        self.database_url = db_config.get("url")
        self.pool_size = db_config.get("pool_size", 5)
        self.max_overflow = db_config.get("max_overflow", 10)
        self.echo = db_config.get("echo", False)

        self.engine = None
        self.session_maker = None

    async def initialize(self):
        """Initialize database engine and create tables."""
        try:
            self.engine = create_async_engine(
                self.database_url,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                echo=self.echo,
            )

            self.session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    async def close(self):
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")

    async def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            if not self.engine:
                return False

            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                return True

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def get_session(self) -> AsyncSession:
        """Get a new database session."""
        return self.session_maker()
