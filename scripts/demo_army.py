"""Army list, ruleset, validation, runtime state, and persistence demo.

Run from the repository root:

    uv run python scripts/demo_army.py
"""

from __future__ import annotations

from grimsim import (
    Army,
    ArmyList,
    Enhancement,
    Ruleset,
    Unit,
    UnitSelection,
    validate_army_list,
)
from grimsim.data import (
    MissingPointsError,
    PointsCatalog,
    connect,
    initialize_schema,
    load_army_list,
    save_army_list,
)
from grimsim.examples import (
    elite_infantry,
    example_detachment,
    example_faction,
    example_points_catalog,
    example_ruleset,
    example_ruleset_alt,
    melee_attacker,
    mixed_melee_unit,
    vehicle,
)
from grimsim.validation import RosterConstraints

POINTS_LIMIT = 2000


def _catalog_or_raise() -> PointsCatalog:
    catalog = example_points_catalog()
    if not catalog.entries:
        raise RuntimeError("Demo data missing: example_points_catalog() is empty.")
    return catalog


def _selection(
    unit: Unit,
    catalog: PointsCatalog,
    ruleset: Ruleset,
    quantity: int = 1,
    enhancements: tuple[Enhancement, ...] = (),
) -> UnitSelection:
    """Look up catalog points for this unit under the list's ruleset."""
    try:
        cost = catalog.cost_for(unit, ruleset, model_count=unit.profile.model_count)
    except MissingPointsError as exc:
        raise RuntimeError(f"Demo data missing: {exc}") from exc
    return UnitSelection(
        unit=unit,
        quantity=quantity,
        points=cost,
        enhancements=enhancements,
    )


def _print_ruleset_costs(
    catalog: PointsCatalog,
    ruleset: Ruleset,
    units: tuple[Unit, ...],
) -> None:
    print(f"Ruleset {ruleset.points_version} ({ruleset.slug}):")
    for unit in units:
        size = unit.profile.model_count
        try:
            cost = catalog.cost_for(unit, ruleset, model_count=size)
        except MissingPointsError as exc:
            raise RuntimeError(f"Demo data missing: {exc}") from exc
        print(f"  {unit.profile.name} x{size}: {cost} pts")


def _selection_label(selection: UnitSelection) -> str:
    name = f"{selection.unit.profile.name} x{selection.size}"
    if selection.quantity > 1:
        name += f" x{selection.quantity}"
    if selection.enhancements:
        extra = ", ".join(e.name for e in selection.enhancements)
        name += f" + {extra}"
    return name


def main() -> None:
    catalog = _catalog_or_raise()
    ruleset_a = example_ruleset()
    ruleset_b = example_ruleset_alt()
    faction = example_faction()
    detachment = example_detachment()

    compared_units = (mixed_melee_unit(), melee_attacker(), elite_infantry(), vehicle())
    for unit in compared_units:
        if unit.id is None:
            raise RuntimeError(f"Demo data missing: {unit.profile.name} has no catalog identity.")

    print("=== GrimSim Army & Ruleset Demo ===")
    print()
    print(f"Faction:      {faction.name}")
    print(f"Detachment:   {detachment.name}")
    print(f"Points Limit: {POINTS_LIMIT}")
    print()

    # Same unit identities and sizes, two published points versions.
    _print_ruleset_costs(catalog, ruleset_a, compared_units)
    print()
    _print_ruleset_costs(catalog, ruleset_b, compared_units)

    warlord = Enhancement(id="exemplar_blade", name="Exemplar Blade", points=25)

    # Build a list under the later ruleset using catalog costs.
    army_list = ArmyList(
        name="Example Crimson Hosts",
        faction=faction,
        detachment=detachment,
        ruleset=ruleset_b,
        points_limit=POINTS_LIMIT,
        selections=(
            _selection(melee_attacker(), catalog, ruleset_b),
            _selection(mixed_melee_unit(), catalog, ruleset_b, quantity=2),
            _selection(
                elite_infantry(),
                catalog,
                ruleset_b,
                enhancements=(warlord,),
            ),
            _selection(vehicle(), catalog, ruleset_b),
        ),
    )

    print()
    print("--- Army List ---")
    print()
    for selection in army_list.selections:
        line_pts = selection.catalog_points(catalog, army_list.ruleset)
        print(f"{_selection_label(selection):<48} {line_pts:>6} pts")
    print()
    catalog_total = army_list.points_cost(catalog)
    remaining = army_list.remaining_catalog_points(catalog)
    print(f"{'Total:':<48} {catalog_total:>6} / {army_list.points_limit} pts")
    print(f"{'Remaining:':<48} {remaining:>6} pts")
    print()
    validation = validate_army_list(army_list, catalog=catalog)
    print(f"Validation: {'VALID' if validation.is_valid else 'INVALID'}")
    if validation.issues:
        print()
        for issue in validation.issues:
            print(f"- [{issue.code}] {issue.message}")

    # Intentionally illegal: over points + too many copies. Do not raise.
    print()
    print("--- Invalid List Example ---")
    print()
    invalid = ArmyList(
        name="Over-capacity",
        faction=faction,
        detachment=detachment,
        ruleset=ruleset_b,
        points_limit=400,
        selections=(
            _selection(melee_attacker(), catalog, ruleset_b, quantity=3),
            _selection(vehicle(), catalog, ruleset_b, quantity=2),
        ),
    )
    constraints = RosterConstraints(max_copies=(("example-berserkers", 1),))
    invalid_result = validate_army_list(invalid, catalog=catalog, constraints=constraints)
    print(f"Validation: {'VALID' if invalid_result.is_valid else 'INVALID'}")
    print()
    for issue in invalid_result.issues:
        print(f"- [{issue.code}] {issue.message}")

    # Runtime army: mutable UnitState, immutable source list.
    army = Army.from_list(army_list)
    print()
    print("--- Runtime Army (from list) ---")
    print()
    print(f"Instantiated units: {len(army.units)}")
    for index, state in enumerate(army.units, start=1):
        print(
            f"  {index}. {state.unit.profile.name}: "
            f"{state.remaining_models}/{state.starting_models} models remaining"
        )

    # Optional in-memory DuckDB round-trip (combat does not need this).
    print()
    print("--- DuckDB persistence (in-memory) ---")
    conn = connect()
    initialize_schema(conn)
    save_army_list(conn, army_list, list_id="demo-list")
    loaded = load_army_list(conn, "demo-list")
    conn.close()
    print(f"Saved and loaded '{loaded.name}'")
    first = loaded.selections[0]
    print(
        f"Selections: {loaded.selection_count}, "
        f"first identity: {first.unit.identity}, "
        f"size: {first.size}"
    )
    print("(Reloaded units restore identity/size/points, not weapon profiles.)")


if __name__ == "__main__":
    main()
