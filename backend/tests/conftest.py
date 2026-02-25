"""Pytest configuration and fixtures for tests."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base


@pytest.fixture(scope="session")
def engine():
    """Create an in-memory SQLite database for tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    # Import all models so they're registered
    import app.models  # noqa: F401

    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db(engine) -> Session:
    """Provide a fresh database session for each test."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
