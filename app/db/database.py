"""
Database setup — async SQLAlchemy.
Works with PostgreSQL on Render and SQLite for local dev.
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


engine = create_async_engine(
    settings.async_database_url,
    echo=False,
    # PostgreSQL-specific pool settings (ignored for SQLite)
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
) if not settings.async_database_url.startswith("sqlite") else create_async_engine(
    settings.async_database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields a DB session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Create all tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
