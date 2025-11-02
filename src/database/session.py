"""
Database Session Management

SQLAlchemy Engine and Session factory for battery data analysis system.
"""

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

from .models import Base

# Default database URL (SQLite)
DEFAULT_DB_URL = "sqlite:///battery_data.db"

# Global engine and session factory
_engine: Engine | None = None
_SessionFactory: sessionmaker | None = None


def init_db(db_url: str = DEFAULT_DB_URL, echo: bool = False) -> Engine:
    """
    Initialize database engine and create tables

    Args:
        db_url: Database URL (default: SQLite)
        echo: Enable SQL echo for debugging

    Returns:
        Engine: SQLAlchemy engine
    """
    global _engine, _SessionFactory

    _engine = create_engine(db_url, echo=echo)

    # Enable foreign key constraints for SQLite
    if db_url.startswith("sqlite"):
        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    # Create all tables
    Base.metadata.create_all(_engine)

    # Create session factory
    _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False)

    return _engine


def get_engine() -> Engine:
    """
    Get database engine

    Returns:
        Engine: SQLAlchemy engine

    Raises:
        RuntimeError: If database not initialized
    """
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _engine


def get_session() -> Session:
    """
    Get database session

    Returns:
        Session: SQLAlchemy session

    Raises:
        RuntimeError: If database not initialized
    """
    if _SessionFactory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _SessionFactory()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    Context manager for database session with automatic commit/rollback

    Usage:
        with session_scope() as session:
            project = TestProject(name="Test Project")
            session.add(project)
            # Auto-commit on success, auto-rollback on exception

    Yields:
        Session: SQLAlchemy session
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def drop_all_tables(engine: Engine | None = None) -> None:
    """
    Drop all tables (WARNING: destroys all data)

    Args:
        engine: SQLAlchemy engine (default: global engine)
    """
    if engine is None:
        engine = get_engine()
    Base.metadata.drop_all(engine)


def create_all_tables(engine: Engine | None = None) -> None:
    """
    Create all tables

    Args:
        engine: SQLAlchemy engine (default: global engine)
    """
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)


def reset_database(engine: Engine | None = None) -> None:
    """
    Reset database (drop and recreate all tables)

    WARNING: This destroys all data

    Args:
        engine: SQLAlchemy engine (default: global engine)
    """
    if engine is None:
        engine = get_engine()
    drop_all_tables(engine)
    create_all_tables(engine)
