"""Campaign region order, victory events, and item requirement logic."""

from typing import Dict, List, Tuple

from .Locations import location_table

# Linear campaign order (matches Locations.region)
REGION_ORDER = [
    "Thalgrund",
    "VillageAttack",
    "Crawford",
    "Cleycourt",
    "Flood",
    "Barmecia",
    "Folklung",
    "Norfolk",
    "Kaloix",
    "Plague",
    "OldKingsCastle",
    "CloudyMountains",
    "Evelance",
    "Wasteland",
    "BattleOfEvelance",
]

VICTORY_LOCATION_BY_REGION: Dict[str, str] = {
    "Thalgrund": "thalgrund_victory",
    "VillageAttack": "villageattack_victory",
    "Crawford": "crawford_victory",
    "Cleycourt": "cleycourt_victory",
    "Flood": "flood_victory",
    "Barmecia": "barmecia_victory",
    "Folklung": "folklung_victory",
    "Norfolk": "norfolk_victory",
    "Kaloix": "kaloix_victory",
    "Plague": "plague_victory",
    "OldKingsCastle": "old_kings_castle_victory",
    "CloudyMountains": "cloudy_mountains_victory",
    "Evelance": "evelance_victory",
    "Wasteland": "wasteland_victory",
    "BattleOfEvelance": "battleofevelance_victory",
}

# Items that must be obtainable before finishing a mission (used for region entrances).
MISSION_ITEM_REQUIREMENTS: Dict[str, Dict[str, int]] = {
    "Thalgrund": {"progressive_mercenaries": 1},
    "VillageAttack": {"progressive_literacy": 1},
    "Crawford": {"progressive_construction": 2},
    "Flood": {"ari": 1},
    "Barmecia": {"progressive_literacy": 2},
    "Folklung": {"pilgrim": 1},
    "Plague": {"progressive_weathertech": 1, "progressive_alchemy": 3},
    "OldKingsCastle": {"helias": 1},
    "Evelance": {"progressive_literacy": 4},
    "Wasteland": {"progressive_construction": 4},
}

THALGRUND_LOCATION_ORDER: List[str] = [
    "thalgrund_save_village",
    "thalgrund_speak_with_priest",
    "thalgrund_sword_mayor",
    "thalgrund_bow_mayor",
    "thalgrund_leonardo",
    "thalgrund_ring_quest",
    "thalgrund_river_yacht_villager",
    "thalgrund_build_barracks",
    "thalgrund_victory",
]

THALGRUND_ITEM_GATE = "thalgrund_build_barracks"

def region_entrance_requirements(region: str) -> Tuple[str, Dict[str, int]]:
    index = REGION_ORDER.index(region)
    if index == 0:
        return "", {}

    prev_region = REGION_ORDER[index - 1]
    required_location = VICTORY_LOCATION_BY_REGION[prev_region]

    items: Dict[str, int] = {}
    for req_region in REGION_ORDER[: index + 1]:
        for item, count in MISSION_ITEM_REQUIREMENTS.get(req_region, {}).items():
            items[item] = max(items.get(item, 0), count)

    return required_location, items


def build_location_item_requirements() -> Dict[str, Dict[str, int]]:
    """Per-location item rules. Missions without explicit gates apply to every check in the region."""
    requirements: Dict[str, Dict[str, int]] = {}

    gate_index = THALGRUND_LOCATION_ORDER.index(THALGRUND_ITEM_GATE)
    mercenaries = MISSION_ITEM_REQUIREMENTS["Thalgrund"]
    for location_name in THALGRUND_LOCATION_ORDER[gate_index:]:
        requirements[location_name] = dict(mercenaries)

    for region_name, items in MISSION_ITEM_REQUIREMENTS.items():
        if region_name == "Thalgrund":
            continue
        victory_name = VICTORY_LOCATION_BY_REGION[region_name]
        for location_name, location_data in location_table.items():
            if location_data.region != region_name or location_name == victory_name:
                continue
            requirements[location_name] = dict(items)

    return requirements
