"""Fictional example unit profiles and army-list demos.

These are generic numeric profiles — not copied datasheet text.
"""

from __future__ import annotations

from datetime import date

from grimsim.models.ability import (
    FeelNoPain,
    LethalHits,
    RerollHitOnes,
    RerollWoundOnes,
    SustainedHits,
)
from grimsim.models.army import Army
from grimsim.models.army_list import ArmyList
from grimsim.models.detachment import Detachment
from grimsim.models.dice import DiceExpression
from grimsim.models.enhancement import Enhancement
from grimsim.models.faction import Faction
from grimsim.models.ruleset import Ruleset
from grimsim.models.selection import UnitSelection
from grimsim.models.unit import Unit, UnitProfile
from grimsim.models.weapon import Weapon, WeaponProfile
from grimsim.validation import validate_army_list


def melee_attacker() -> Unit:
    """Aggressive melee infantry with Sustained Hits and Lethal Hits."""
    axe = Weapon(
        profile=WeaponProfile(
            name="Chain Axe",
            attacks=4,
            skill=3,
            strength=5,
            ap=-2,
            damage=2,
        ),
        abilities=(SustainedHits(1), LethalHits()),
    )
    return Unit(
        profile=UnitProfile(
            name="Example Berserkers",
            model_count=10,
            toughness=4,
            wounds_per_model=2,
            save=3,
            objective_control=1,
        ),
        weapons=(axe,),
        abilities=(RerollHitOnes(),),
    )


def light_infantry() -> Unit:
    """Fragile horde infantry — typical soft shooting target."""
    las = Weapon(
        profile=WeaponProfile(
            name="Lasrifle",
            attacks=2,
            skill=4,
            strength=3,
            ap=0,
            damage=1,
        ),
    )
    return Unit(
        profile=UnitProfile(
            name="Example Troopers",
            model_count=10,
            toughness=3,
            wounds_per_model=1,
            save=5,
            objective_control=2,
        ),
        weapons=(las,),
    )


def elite_infantry() -> Unit:
    """Durable elite infantry with Feel No Pain and an invulnerable save."""
    bolter = Weapon(
        profile=WeaponProfile(
            name="Bolt Rifle",
            attacks=2,
            skill=3,
            strength=4,
            ap=-1,
            damage=1,
        ),
        abilities=(RerollWoundOnes(),),
    )
    return Unit(
        profile=UnitProfile(
            name="Example Veterans",
            model_count=5,
            toughness=4,
            wounds_per_model=3,
            save=3,
            invulnerable_save=5,
            objective_control=1,
        ),
        weapons=(bolter,),
        abilities=(FeelNoPain(5),),
    )


def vehicle() -> Unit:
    """Single-model vehicle with high toughness and multi-damage guns."""
    cannon = Weapon(
        profile=WeaponProfile(
            name="Battle Cannon",
            attacks=DiceExpression.d6(),
            skill=4,
            strength=8,
            ap=-2,
            damage=DiceExpression.d6(),
        ),
    )
    return Unit(
        profile=UnitProfile(
            name="Example Battle Tank",
            model_count=1,
            toughness=10,
            wounds_per_model=12,
            save=2,
            invulnerable_save=5,
            objective_control=3,
        ),
        weapons=(cannon,),
    )


def example_ruleset() -> Ruleset:
    """Sample rules/points environment."""
    return Ruleset(
        id="10th-balanced-2025.01",
        edition="10th",
        rules_version="0.2.0",
        points_version="2025.01",
        effective_date=date(2025, 1, 1),
    )


def example_faction() -> Faction:
    """Fictional faction identity."""
    return Faction(id="crimson_hosts", name="Crimson Hosts")


def example_detachment() -> Detachment:
    """Fictional detachment for the example faction."""
    return Detachment(
        id="blood_tide",
        name="Blood Tide",
        faction_id="crimson_hosts",
        abilities=(RerollHitOnes(),),
    )


def example_army_list(*, points_limit: int = 2000) -> ArmyList:
    """Build a fictional 2,000-point roster for demos and tests."""
    warlord_enhancement = Enhancement(
        id="exemplar_blade",
        name="Exemplar Blade",
        points=25,
    )
    # Points total: 360 + 240 + 225 + 440 + 180 + 240 + 200 + 110 = 1995
    return ArmyList(
        name="Example Crimson Hosts",
        faction=example_faction(),
        detachment=example_detachment(),
        ruleset=example_ruleset(),
        points_limit=points_limit,
        selections=(
            UnitSelection(unit=melee_attacker(), quantity=2, points=180),  # 360
            UnitSelection(unit=light_infantry(), quantity=2, points=120),  # 240
            UnitSelection(
                unit=elite_infantry(),
                quantity=1,
                points=200,
                enhancements=(warlord_enhancement,),
            ),  # 225
            UnitSelection(unit=vehicle(), quantity=2, points=220),  # 440
            UnitSelection(unit=melee_attacker(), quantity=1, points=180),  # 180
            UnitSelection(unit=light_infantry(), quantity=2, points=120),  # 240
            UnitSelection(unit=elite_infantry(), quantity=1, points=200),  # 200
            UnitSelection(unit=vehicle(), quantity=1, points=110),  # 110
        ),
    )


def example_validated_army() -> tuple[ArmyList, Army]:
    """Create a validated list and a runtime Army from it."""
    army_list = example_army_list()
    validation = validate_army_list(army_list)
    if not validation.is_valid:
        codes = ", ".join(issue.code for issue in validation.errors)
        raise ValueError(f"example army list is invalid: {codes}")
    return army_list, Army.from_list(army_list)


EXAMPLE_UNITS: dict[str, Unit] = {
    "melee_attacker": melee_attacker(),
    "light_infantry": light_infantry(),
    "elite_infantry": elite_infantry(),
    "vehicle": vehicle(),
}
