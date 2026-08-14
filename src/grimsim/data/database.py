"""Minimal DuckDB persistence foundation.

Combat resolution does not depend on this module. The simulation engine
works fully without a database.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

RULES_VERSIONS_DDL = """
CREATE TABLE IF NOT EXISTS rules_versions (
    id INTEGER PRIMARY KEY,
    edition VARCHAR NOT NULL,
    rules_version VARCHAR NOT NULL,
    points_version VARCHAR NOT NULL,
    effective_date DATE NOT NULL
);
"""

SIMULATION_RUNS_DDL = """
CREATE TABLE IF NOT EXISTS simulation_runs (
    id INTEGER PRIMARY KEY,
    rules_version_id INTEGER,
    created_at TIMESTAMP DEFAULT current_timestamp,
    iterations INTEGER NOT NULL,
    seed BIGINT,
    attacker_name VARCHAR,
    weapon_name VARCHAR,
    target_name VARCHAR,
    mean_damage DOUBLE,
    mean_models_killed DOUBLE,
    probability_target_destroyed DOUBLE,
    FOREIGN KEY (rules_version_id) REFERENCES rules_versions(id)
);
"""


def connect(path: str | Path | None = None) -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection.

    Args:
        path: File path for a persistent database, or ``None`` for in-memory.
    """
    if path is None:
        return duckdb.connect(database=":memory:")
    return duckdb.connect(database=str(path))


def initialize_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Create the minimal persistence tables if they do not exist."""
    conn.execute(RULES_VERSIONS_DDL)
    conn.execute(SIMULATION_RUNS_DDL)


def insert_rules_version(
    conn: duckdb.DuckDBPyConnection,
    *,
    version_id: int,
    edition: str,
    rules_version: str,
    points_version: str,
    effective_date: str,
) -> None:
    """Insert a row into ``rules_versions``.

    Args:
        effective_date: ISO date string ``YYYY-MM-DD``.
    """
    conn.execute(
        """
        INSERT INTO rules_versions (id, edition, rules_version, points_version, effective_date)
        VALUES (?, ?, ?, ?, ?)
        """,
        [version_id, edition, rules_version, points_version, effective_date],
    )
