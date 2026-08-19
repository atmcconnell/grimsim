"""Data persistence package."""

from grimsim.data.database import (
    connect,
    initialize_schema,
    insert_rules_version,
    save_ruleset,
)
from grimsim.data.points import MissingPointsError, PointsCatalog, PointsEntry
from grimsim.data.profiles import MissingProfileError, ProfileCatalog, ProfileEntry
from grimsim.data.repository import (
    load_army_list,
    save_army_list,
    save_simulation_summary,
    simulation_summary_id,
)

__all__ = [
    "MissingPointsError",
    "MissingProfileError",
    "PointsCatalog",
    "PointsEntry",
    "ProfileCatalog",
    "ProfileEntry",
    "connect",
    "initialize_schema",
    "insert_rules_version",
    "load_army_list",
    "save_army_list",
    "save_ruleset",
    "save_simulation_summary",
    "simulation_summary_id",
]
