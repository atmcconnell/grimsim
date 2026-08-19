"""Tests for DuckDB persistence foundation and ML placeholder."""

from __future__ import annotations

from datetime import date

import pytest

from grimsim.data.database import (
    connect,
    initialize_schema,
    insert_rules_version,
    save_ruleset,
)
from grimsim.data.repository import load_army_list, save_army_list, save_simulation_summary
from grimsim.examples import example_army_list
from grimsim.ml.matchup_model import MatchupFeatures, MatchupModelPlaceholder
from grimsim.models.ruleset import Ruleset
from grimsim.validation import validate_army_list


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
    ruleset_rows = conn.execute(
        "SELECT id, edition FROM rulesets WHERE id = 'legacy-1'"
    ).fetchall()
    assert ruleset_rows == [("legacy-1", "10th")]
    conn.close()


def test_save_and_load_ruleset() -> None:
    conn = connect()
    initialize_schema(conn)
    ruleset = Ruleset(
        id="10th-balanced-2025.01",
        edition="10th",
        rules_version="0.2.0",
        points_version="2025.01",
        effective_date=date(2025, 1, 1),
    )
    save_ruleset(conn, ruleset)
    row = conn.execute(
        "SELECT edition, rules_version, points_version FROM rulesets WHERE id = ?",
        [ruleset.slug],
    ).fetchone()
    assert row == ("10th", "0.2.0", "2025.01")
    conn.close()


def test_save_and_load_army_list() -> None:
    conn = connect()
    initialize_schema(conn)
    original = example_army_list()
    assert validate_army_list(original).is_valid

    save_army_list(conn, original, list_id="example-1")
    loaded = load_army_list(conn, "example-1")

    assert loaded.name == original.name
    assert loaded.faction.id == original.faction.id
    assert loaded.detachment.id == original.detachment.id
    assert loaded.ruleset.slug == original.ruleset.slug
    assert loaded.points_limit == original.points_limit
    assert loaded.total_points == original.total_points
    assert loaded.selection_count == original.selection_count
    assert loaded.selections[0].unit.profile.name == (
        original.selections[0].unit.profile.name
    )
    conn.close()


def test_save_simulation_summary_is_deterministic() -> None:
    conn = connect()
    initialize_schema(conn)
    kwargs = dict(
        simulation_type="unit_activation",
        attacker_name="A",
        target_name="B",
        attack_plan="disjoint: 4x Chainblade; 1x Power Maul",
        iterations=1000,
        seed=42,
        mean_damage=3.5,
        median_damage=3.0,
        std_damage=1.2,
        mean_models_killed=3.1,
        median_models_killed=3.0,
        min_models_killed=0,
        max_models_killed=8,
        probability_target_destroyed=0.01,
        ruleset_id="10th-balanced-2025.01",
    )
    id_a = save_simulation_summary(conn, **kwargs)
    id_b = save_simulation_summary(conn, **kwargs)
    assert id_a == id_b
    assert len(id_a) == 64
    row = conn.execute(
        "SELECT simulation_type, iterations, mean_damage FROM simulation_summaries WHERE id = ?",
        [id_a],
    ).fetchone()
    assert row == ("unit_activation", 1000, 3.5)
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
