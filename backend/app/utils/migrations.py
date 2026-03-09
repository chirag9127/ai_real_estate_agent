"""Lightweight migration utility.

SQLAlchemy's ``create_all()`` creates missing *tables* but never adds new
columns to tables that already exist.  This helper inspects the live database
schema and emits ``ALTER TABLE … ADD COLUMN`` for any columns defined in the
ORM models that are absent from the database.
"""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.database import Base

logger = logging.getLogger(__name__)


def run_migrations(engine: Engine) -> None:
    """Compare ORM metadata against the live schema and add missing columns."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table_name, table in Base.metadata.tables.items():
            if table_name not in existing_tables:
                # Table doesn't exist yet; create_all() will handle it.
                continue

            existing_columns = {
                col["name"] for col in inspector.get_columns(table_name)
            }

            for column in table.columns:
                if column.name in existing_columns:
                    continue

                # Build a portable column type string
                col_type = column.type.compile(dialect=engine.dialect)
                nullable = "NULL" if column.nullable else "NOT NULL"

                stmt = f'ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type} {nullable}'
                logger.info("Migration: %s", stmt)
                conn.execute(text(stmt))

    logger.info("Migration check complete.")
