"""
WhiteMagic API - Database Models

SQLAlchemy models for PostgreSQL database.
Supports async operations with asyncpg driver.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class User(Base):
    """User model - represents a WhiteMagic user."""

    __tablename__ = "users"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # User identification
    email = Column(String(255), unique=True, nullable=False, index=True)
    whop_user_id = Column(String(255), unique=True, nullable=True, index=True)
    whop_membership_id = Column(String(255), unique=True, nullable=True)

    # Plan information
    plan_tier = Column(String(50), nullable=False, default="free", index=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    last_seen_at = Column(DateTime, nullable=True)

    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="user", cascade="all, delete-orphan")
    quota = relationship(
        "Quota", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, plan={self.plan_tier})>"


class APIKey(Base):
    """API Key model - stores hashed API keys for authentication."""

    __tablename__ = "api_keys"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Foreign key
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Key data (NEVER store raw keys!)
    key_hash = Column(String(128), unique=True, nullable=False, index=True)
    key_prefix = Column(String(16), nullable=False)  # For display: "wm_prod_abc123..."

    # Metadata
    name = Column(String(100), nullable=True)  # User-provided name like "Production Key"

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=func.now())
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    # Status
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    user = relationship("User", back_populates="api_keys")
    usage_records = relationship("UsageRecord", back_populates="api_key")

    # Indexes
    __table_args__ = (Index("idx_api_keys_user_active", user_id, is_active),)

    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, prefix={self.key_prefix}, active={self.is_active})>"


class UsageRecord(Base):
    """Usage Record model - tracks API usage for analytics and billing."""

    __tablename__ = "usage_records"

    # Primary key - use Integer for SQLite compatibility
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    api_key_id = Column(
        UUID(as_uuid=True), ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True
    )

    # Request information
    endpoint = Column(String(100), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)

    # Timestamp
    created_at = Column(DateTime, nullable=False, default=func.now(), index=True)

    # Generated date column for efficient queries
    date = Column(Date, nullable=False, default=func.current_date(), index=True)

    # Relationships
    user = relationship("User", back_populates="usage_records")
    api_key = relationship("APIKey", back_populates="usage_records")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_usage_user_date", user_id, date),
        Index("idx_usage_date_endpoint", date, endpoint),
    )

    def __repr__(self) -> str:
        return f"<UsageRecord(id={self.id}, user_id={self.user_id}, endpoint={self.endpoint})>"


class Quota(Base):
    """Quota model - tracks usage quotas and limits per user."""

    __tablename__ = "quotas"

    # Primary key (one-to-one with User)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    # Request quotas
    requests_today = Column(Integer, nullable=False, default=0)
    requests_this_month = Column(Integer, nullable=False, default=0)

    # Resource quotas
    memories_count = Column(Integer, nullable=False, default=0)
    storage_bytes = Column(BigInteger, nullable=False, default=0)

    # Reset tracking
    last_reset_daily: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    last_reset_monthly: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    # Relationships
    user = relationship("User", back_populates="quota")

    def __repr__(self) -> str:
        return f"<Quota(user_id={self.user_id}, requests_today={self.requests_today})>"


# Database connection and session management


class Database:
    """Database connection manager."""

    def __init__(self, database_url: str, echo: bool = False):
        """
        Initialize database connection.

        Args:
            database_url: PostgreSQL connection URL (async format)
                         Example: postgresql+asyncpg://user:pass@host/db
            echo: Whether to echo SQL statements (for debugging)
        """
        # Configure engine based on database type
        # SQLite doesn't support connection pooling
        if "sqlite" in database_url:
            self.engine = create_async_engine(
                database_url,
                echo=echo,
                connect_args={"check_same_thread": False},
            )
        else:
            # PostgreSQL / other databases
            self.engine = create_async_engine(
                database_url,
                echo=echo,
                pool_size=20,
                max_overflow=0,
                pool_pre_ping=True,  # Verify connections before using
            )

        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def create_tables(self):
        """Create all tables in the database."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self):
        """Drop all tables (use with caution!)."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def close(self):
        """Close database connection."""
        await self.engine.dispose()

    def get_session(self) -> AsyncSession:
        """Get a new database session."""
        return self.async_session()


# Convenience function for tests and scripts
async def get_database(database_url: str, echo: bool = False) -> Database:
    """
    Get a configured database instance.

    Args:
        database_url: PostgreSQL connection URL
        echo: Whether to echo SQL statements

    Returns:
        Configured Database instance
    """
    return Database(database_url, echo=echo)
