"""Persistence adapters for army-list domain objects.

Domain models have no ``.save()`` methods — call these helpers instead.
"""

from __future__ import annotations

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
                id, army_list_id, position, unit_name, model_count, toughness,
                wounds_per_model, save, invulnerable_save, quantity, points,
                enhancement_ids, enhancement_names, enhancement_points
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                _selection_row_id(list_id, position),
                list_id,
                position,
                profile.name,
                profile.model_count,
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
        SELECT unit_name, model_count, toughness, wounds_per_model, save,
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
        )
        selections.append(
            UnitSelection(
                unit=unit,
                quantity=quantity,
                points=points,
                enhancements=enhancements,
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
    """Deterministic integer PK for a selection row."""
    return abs(hash((list_id, position))) % (2**31 - 1)
