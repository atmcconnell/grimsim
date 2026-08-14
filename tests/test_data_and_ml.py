"""Tests for DuckDB persistence foundation and ML placeholder."""

from __future__ import annotations

import pytest

from grimsim.data.database import connect, initialize_schema, insert_rules_version
from grimsim.ml.matchup_model import MatchupFeatures, MatchupModelPlaceholder


def test_duckdb_schema_and_insert() -> None:
    conn = connect()
    initialize_schema(conn)
    insert_rules_version(
        conn,
        version_id=1,
        edition="10th",
        rules_version="0.1.0",
        points_version="2025.01",
        effective_date="2025-01-01",
    )
    rows = conn.execute("SELECT edition, rules_version FROM rules_versions").fetchall()
    assert rows == [("10th", "0.1.0")]
    conn.close()


def test_matchup_model_placeholder() -> None:
    model = MatchupModelPlaceholder()
    features = MatchupFeatures(
        attacker_army="Red",
        defender_army="Blue",
        mission="Take and Hold",
        rules_version="0.1.0",
    )
    with pytest.raises(NotImplementedError, match="not implemented"):
        model.predict(features)
