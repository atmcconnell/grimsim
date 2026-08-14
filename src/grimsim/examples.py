"""Fictional example unit profiles for demos and tests.

These are generic numeric profiles — not copied datasheet text.
"""

from __future__ import annotations

from grimsim.models.ability import (
    FeelNoPain,
    LethalHits,
    RerollHitOnes,
    RerollWoundOnes,
    SustainedHits,
)
from grimsim.models.dice import DiceExpression
from grimsim.models.unit import Unit, UnitProfile
from grimsim.models.weapon import Weapon, WeaponProfile


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


EXAMPLE_UNITS: dict[str, Unit] = {
    "melee_attacker": melee_attacker(),
    "light_infantry": light_infantry(),
    "elite_infantry": elite_infantry(),
    "vehicle": vehicle(),
}
