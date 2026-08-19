"""Persistence adapters for army-list domain objects.

Domain models have no ``.save()`` methods — call these helpers instead.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date

import duckdb

from grimsim.data.database import save_ruleset
from grimsim.models.army_list import ArmyList
from grimsim.models.detachment import Detachment
from grimsim.models.enhancement import Enhancement
from grimsim.models.faction import Faction
from grimsim.models.ruleset import Ruleset
from grimsim.models.selection import UnitSelection
from grimsim.models.unit import Unit, UnitProfile


def save_faction(conn: duckdb.DuckDBPyConnection, faction: Faction) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO factions (id, name) VALUES (?, ?)",
        [faction.id, faction.name],
    )


def save_detachment(conn: duckdb.DuckDBPyConnection, detachment: Detachment) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO detachments (id, name, faction_id)
        VALUES (?, ?, ?)
        """,
        [detachment.id, detachment.name, detachment.faction_id],
    )


def save_army_list(
    conn: duckdb.DuckDBPyConnection,
    army_list: ArmyList,
    *,
    list_id: str,
) -> None:
    """Persist an army list and its selections.

    Unit combat details beyond core profile fields are not fully serialized
    in v0.2 — enough is stored to reconstruct roster identity and points.
    """
    if not list_id.strip():
        raise ValueError("list_id must be non-empty")

    save_ruleset(conn, army_list.ruleset)
    save_faction(conn, army_list.faction)
    save_detachment(conn, army_list.detachment)

    conn.execute(
        """
        INSERT OR REPLACE INTO army_lists
            (id, name, faction_id, detachment_id, ruleset_id, points_limit)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            list_id,
            army_list.name,
            army_list.faction.id,
            army_list.detachment.id,
            army_list.ruleset.slug,
            army_list.points_limit,
        ],
    )
    conn.execute("DELETE FROM army_list_selections WHERE army_list_id = ?", [list_id])

    for position, selection in enumerate(army_list.selections):
        profile = selection.unit.profile
        conn.execute(
            """
            INSERT INTO army_list_selections (
                id, army_list_id, position, unit_id, unit_name, model_count, toughness,
                wounds_per_model, save, invulnerable_save, quantity, points,
                enhancement_ids, enhancement_names, enhancement_points
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                _selection_row_id(list_id, position),
                list_id,
                position,
                selection.unit.id,
                profile.name,
                selection.size,
                profile.toughness,
                profile.wounds_per_model,
                profile.save,
                profile.invulnerable_save,
                selection.quantity,
                selection.points,
                json.dumps([e.id for e in selection.enhancements]),
                json.dumps([e.name for e in selection.enhancements]),
                json.dumps([e.points for e in selection.enhancements]),
            ],
        )


def load_army_list(conn: duckdb.DuckDBPyConnection, list_id: str) -> ArmyList:
    """Load an army list previously stored by ``save_army_list``.

    Reconstructed units have empty weapon tuples — sufficient for roster
    validation and runtime ``Army`` instantiation, not for combat demos.
    """
    row = conn.execute(
        """
        SELECT name, faction_id, detachment_id, ruleset_id, points_limit
        FROM army_lists WHERE id = ?
        """,
        [list_id],
    ).fetchone()
    if row is None:
        raise KeyError(f"army list not found: {list_id}")

    name, faction_id, detachment_id, ruleset_id, points_limit = row

    faction_row = conn.execute(
        "SELECT id, name FROM factions WHERE id = ?", [faction_id]
    ).fetchone()
    if faction_row is None:
        raise KeyError(f"faction not found: {faction_id}")
    faction = Faction(id=faction_row[0], name=faction_row[1])

    detachment_row = conn.execute(
        "SELECT id, name, faction_id FROM detachments WHERE id = ?",
        [detachment_id],
    ).fetchone()
    if detachment_row is None:
        raise KeyError(f"detachment not found: {detachment_id}")
    detachment = Detachment(
        id=detachment_row[0],
        name=detachment_row[1],
        faction_id=detachment_row[2],
    )

    ruleset_row = conn.execute(
        """
        SELECT id, edition, rules_version, points_version, effective_date
        FROM rulesets WHERE id = ?
        """,
        [ruleset_id],
    ).fetchone()
    if ruleset_row is None:
        raise KeyError(f"ruleset not found: {ruleset_id}")
    ruleset = Ruleset(
        id=ruleset_row[0],
        edition=ruleset_row[1],
        rules_version=ruleset_row[2],
        points_version=ruleset_row[3],
        effective_date=(
            ruleset_row[4]
            if hasattr(ruleset_row[4], "year")
            else date.fromisoformat(str(ruleset_row[4]))
        ),
    )

    selection_rows = conn.execute(
        """
        SELECT unit_id, unit_name, model_count, toughness, wounds_per_model, save,
               invulnerable_save, quantity, points,
               enhancement_ids, enhancement_names, enhancement_points
        FROM army_list_selections
        WHERE army_list_id = ?
        ORDER BY position
        """,
        [list_id],
    ).fetchall()

    selections: list[UnitSelection] = []
    for sel in selection_rows:
        (
            unit_id,
            unit_name,
            model_count,
            toughness,
            wounds_per_model,
            save,
            invulnerable_save,
            quantity,
            points,
            enhancement_ids_json,
            enhancement_names_json,
            enhancement_points_json,
        ) = sel
        enhancements = tuple(
            Enhancement(id=eid, name=ename, points=epoints)
            for eid, ename, epoints in zip(
                json.loads(enhancement_ids_json),
                json.loads(enhancement_names_json),
                json.loads(enhancement_points_json),
                strict=True,
            )
        )
        unit = Unit(
            profile=UnitProfile(
                name=unit_name,
                model_count=model_count,
                toughness=toughness,
                wounds_per_model=wounds_per_model,
                save=save,
                invulnerable_save=invulnerable_save,
            ),
            weapons=(),
            id=unit_id or None,
        )
        selections.append(
            UnitSelection(
                unit=unit,
                quantity=quantity,
                points=points,
                enhancements=enhancements,
                model_count=model_count,
            )
        )

    return ArmyList(
        name=name,
        faction=faction,
        detachment=detachment,
        ruleset=ruleset,
        selections=tuple(selections),
        points_limit=points_limit,
    )


def _selection_row_id(list_id: str, position: int) -> int:
    """Deterministic integer PK for a selection row (stable across processes)."""
    digest = hashlib.sha256(f"{list_id}:{position}".encode()).hexdigest()
    return int(digest[:8], 16) % (2**31 - 1)


def simulation_summary_id(
    *,
    simulation_type: str,
    attacker_name: str,
    target_name: str,
    attack_plan: str,
    iterations: int,
    seed: int | None,
    ruleset_id: str | None,
) -> str:
    """Stable SHA-256 id from serialized simulation inputs (not ``hash()``)."""
    payload = json.dumps(
        {
            "simulation_type": simulation_type,
            "attacker_name": attacker_name,
            "target_name": target_name,
            "attack_plan": attack_plan,
            "iterations": iterations,
            "seed": seed,
            "ruleset_id": ruleset_id,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def save_simulation_summary(
    conn: duckdb.DuckDBPyConnection,
    *,
    simulation_type: str,
    attacker_name: str,
    target_name: str,
    attack_plan: str,
    iterations: int,
    seed: int | None,
    mean_damage: float,
    median_damage: float,
    std_damage: float,
    mean_models_killed: float,
    median_models_killed: float,
    min_models_killed: int,
    max_models_killed: int,
    probability_target_destroyed: float,
    ruleset_id: str | None = None,
) -> str:
    """Persist a Monte Carlo summary row. Returns the stable summary id."""
    summary_id = simulation_summary_id(
        simulation_type=simulation_type,
        attacker_name=attacker_name,
        target_name=target_name,
        attack_plan=attack_plan,
        iterations=iterations,
        seed=seed,
        ruleset_id=ruleset_id,
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO simulation_summaries (
            id, ruleset_id, simulation_type, attacker_name, target_name,
            attack_plan, iterations, seed, mean_damage, median_damage, std_damage,
            mean_models_killed, median_models_killed, min_models_killed,
            max_models_killed, probability_target_destroyed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            summary_id,
            ruleset_id,
            simulation_type,
            attacker_name,
            target_name,
            attack_plan,
            iterations,
            seed,
            mean_damage,
            median_damage,
            std_damage,
            mean_models_killed,
            median_models_killed,
            min_models_killed,
            max_models_killed,
            probability_target_destroyed,
        ],
    )
    return summary_id
