"""Unit tests for the lightweight migration utility."""

from __future__ import annotations

import os
import sys

import pytest
from sqlalchemy import Column, Integer, String, Text, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Isolated Base & model for testing (avoids touching production Base)
# ---------------------------------------------------------------------------

class _TestBase(DeclarativeBase):
    pass


class _FakeModel(_TestBase):
    __tablename__ = "test_migration_table"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    score = Column(Integer, nullable=True)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRunMigrations:
    """Test that run_migrations adds missing columns without error."""

    def _make_engine(self):
        return create_engine("sqlite:///:memory:")

    def test_adds_missing_columns(self):
        """Create a table with only 'id' and 'name', then verify migration
        adds 'description' and 'score'."""
        engine = self._make_engine()

        # Manually create table with only two columns
        with engine.begin() as conn:
            conn.execute(text(
                "CREATE TABLE test_migration_table (id INTEGER PRIMARY KEY, name VARCHAR(100))"
            ))

        inspector = inspect(engine)
        cols_before = {c["name"] for c in inspector.get_columns("test_migration_table")}
        assert "description" not in cols_before
        assert "score" not in cols_before

        # Monkey-patch our test Base into the migration module
        import app.utils.migrations as mig_mod
        original_base = mig_mod.Base
        mig_mod.Base = _TestBase
        try:
            mig_mod.run_migrations(engine)
        finally:
            mig_mod.Base = original_base

        # Verify columns were added
        inspector = inspect(engine)
        cols_after = {c["name"] for c in inspector.get_columns("test_migration_table")}
        assert "description" in cols_after
        assert "score" in cols_after

    def test_no_op_when_columns_exist(self):
        """If all columns already exist, migration should be a no-op."""
        engine = self._make_engine()

        # Create the full table via ORM
        _TestBase.metadata.create_all(engine)

        inspector = inspect(engine)
        cols_before = {c["name"] for c in inspector.get_columns("test_migration_table")}

        import app.utils.migrations as mig_mod
        original_base = mig_mod.Base
        mig_mod.Base = _TestBase
        try:
            mig_mod.run_migrations(engine)
        finally:
            mig_mod.Base = original_base

        cols_after = {c["name"] for c in inspector.get_columns("test_migration_table")}
        assert cols_before == cols_after

    def test_skips_nonexistent_tables(self):
        """If a table in metadata doesn't exist in the DB, it should be skipped
        (create_all handles table creation separately)."""
        engine = self._make_engine()
        # Don't create any tables — migration should not raise

        import app.utils.migrations as mig_mod
        original_base = mig_mod.Base
        mig_mod.Base = _TestBase
        try:
            mig_mod.run_migrations(engine)  # Should not raise
        finally:
            mig_mod.Base = original_base
