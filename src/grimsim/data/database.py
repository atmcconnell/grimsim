"""DuckDB schema and connection helpers.

Combat resolution does not depend on this module.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from grimsim.models.ruleset import Ruleset

RULESETS_DDL = """
CREATE TABLE IF NOT EXISTS rulesets (
    id VARCHAR PRIMARY KEY,
    edition VARCHAR NOT NULL,
    rules_version VARCHAR NOT NULL,
    points_version VARCHAR NOT NULL,
    effective_date DATE NOT NULL
);
"""

# Backward-compatible alias table aligned with the Ruleset domain object.
RULES_VERSIONS_DDL = """
CREATE TABLE IF NOT EXISTS rules_versions (
    id INTEGER PRIMARY KEY,
    edition VARCHAR NOT NULL,
    rules_version VARCHAR NOT NULL,
    points_version VARCHAR NOT NULL,
    effective_date DATE NOT NULL
);
"""

FACTIONS_DDL = """
CREATE TABLE IF NOT EXISTS factions (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL
);
"""

DETACHMENTS_DDL = """
CREATE TABLE IF NOT EXISTS detachments (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    faction_id VARCHAR NOT NULL,
    FOREIGN KEY (faction_id) REFERENCES factions(id)
);
"""

ARMY_LISTS_DDL = """
CREATE TABLE IF NOT EXISTS army_lists (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    faction_id VARCHAR NOT NULL,
    detachment_id VARCHAR NOT NULL,
    ruleset_id VARCHAR NOT NULL,
    points_limit INTEGER NOT NULL,
    FOREIGN KEY (faction_id) REFERENCES factions(id),
    FOREIGN KEY (detachment_id) REFERENCES detachments(id),
    FOREIGN KEY (ruleset_id) REFERENCES rulesets(id)
);
"""

ARMY_LIST_SELECTIONS_DDL = """
CREATE TABLE IF NOT EXISTS army_list_selections (
    id INTEGER PRIMARY KEY,
    army_list_id VARCHAR NOT NULL,
    position INTEGER NOT NULL,
    unit_name VARCHAR NOT NULL,
    model_count INTEGER NOT NULL,
    toughness INTEGER NOT NULL,
    wounds_per_model INTEGER NOT NULL,
    save INTEGER NOT NULL,
    invulnerable_save INTEGER,
    quantity INTEGER NOT NULL,
    points INTEGER NOT NULL,
    enhancement_ids VARCHAR NOT NULL,
    enhancement_names VARCHAR NOT NULL,
    enhancement_points VARCHAR NOT NULL,
    FOREIGN KEY (army_list_id) REFERENCES army_lists(id)
);
"""

SIMULATION_RUNS_DDL = """
CREATE TABLE IF NOT EXISTS simulation_runs (
    id INTEGER PRIMARY KEY,
    ruleset_id VARCHAR,
    rules_version_id INTEGER,
    created_at TIMESTAMP DEFAULT current_timestamp,
    iterations INTEGER NOT NULL,
    seed BIGINT,
    attacker_name VARCHAR,
    weapon_name VARCHAR,
    target_name VARCHAR,
    mean_damage DOUBLE,
    mean_models_killed DOUBLE,
    probability_target_destroyed DOUBLE
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
    """Create persistence tables if they do not exist."""
    conn.execute(RULESETS_DDL)
    conn.execute(RULES_VERSIONS_DDL)
    conn.execute(FACTIONS_DDL)
    conn.execute(DETACHMENTS_DDL)
    conn.execute(ARMY_LISTS_DDL)
    conn.execute(ARMY_LIST_SELECTIONS_DDL)
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
    """Insert into the legacy ``rules_versions`` table and mirrored ``rulesets``.

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
    # Keep rulesets aligned for new code paths.
    slug = f"legacy-{version_id}"
    conn.execute(
        """
        INSERT INTO rulesets (id, edition, rules_version, points_version, effective_date)
        VALUES (?, ?, ?, ?, ?)
        """,
        [slug, edition, rules_version, points_version, effective_date],
    )


def save_ruleset(conn: duckdb.DuckDBPyConnection, ruleset: Ruleset) -> None:
    """Persist a ``Ruleset`` domain object into ``rulesets``."""
    conn.execute(
        """
        INSERT OR REPLACE INTO rulesets
            (id, edition, rules_version, points_version, effective_date)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            ruleset.slug,
            ruleset.edition,
            ruleset.rules_version,
            ruleset.points_version,
            ruleset.effective_date.isoformat(),
        ],
    )
