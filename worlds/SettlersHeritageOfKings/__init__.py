from typing import Dict, Set

from BaseClasses import Region, Tutorial
from worlds.AutoWorld import WebWorld, World
from worlds.generic.Rules import set_rule

from .Items import ItemClassification, SettlersItem, item_table
from .Locations import SettlersLocation, location_table
from .Options import SettlersGameOptions
from .Rules import (
    REGION_ORDER,
    VICTORY_LOCATION_BY_REGION,
    build_location_item_requirements,
    region_entrance_requirements,
)


class SettlersWeb(WebWorld):
    theme = "stone"

    setup = Tutorial(
        "Multiworld Setup Guide",
        "A guide to setting up the Archipelago Settlers client on your computer.",
        "English",
        "setup_en.md",
        authors=["ZorkManu"],
        link="coming soon",
    )
    game_info_languages = ["en"]
    tutorials = [setup]


class SettlersWorld(World):
    """
    Settlers: Heritage of Kings is a real-time strategy game where the player builds a settlement,
    collects resources, and manages settlers.
    """
    game = "SettlersHeritageOfKings"
    web = SettlersWeb()
    options = SettlersGameOptions
    options_dataclass = SettlersGameOptions
    location_name_to_id = {name: data.address for name, data in location_table.items()}
    item_name_to_id = {name: data.code for name, data in item_table.items()}

    data_version = 1

    def create_regions(self) -> None:
        menu_region = Region("Menu", self.player, self.multiworld)
        self.multiworld.regions.append(menu_region)

        regions: Dict[str, Region] = {}
        for location_name, location_data in location_table.items():
            region_name = location_data.region
            if region_name not in regions:
                region = Region(region_name, self.player, self.multiworld)
                regions[region_name] = region
                self.multiworld.regions.append(region)
            regions[region_name].locations.append(
                SettlersLocation(self.player, location_name, location_data.address, regions[region_name])
            )

        menu_region.connect(regions["Thalgrund"])

        for index in range(1, len(REGION_ORDER)):
            prev_region_name = REGION_ORDER[index - 1]
            region_name = REGION_ORDER[index]
            regions[prev_region_name].connect(regions[region_name])

    def create_item(self, name: str) -> SettlersItem:
        item_data = item_table[name]
        return SettlersItem(name=name, code=item_data.code, player=self.player, classification=item_data.type)

    def create_items(self) -> None:
        starting_names: Set[str] = set()

        hero = self.options.starting_hero.current_key
        self.multiworld.push_precollected(self.create_item(hero))
        starting_names.add(hero)

        if self.options.starting_unit != "disabled":
            unit_name = f"progressive_{self.options.starting_unit.current_key}"
            if unit_name in self.item_name_to_id:
                self.multiworld.push_precollected(self.create_item(unit_name))
                starting_names.add(unit_name)

        itempool: list[SettlersItem] = []
        for name in item_table:
            if name in starting_names:
                continue
            for _ in range(item_table[name].quantity):
                itempool.append(self.create_item(name))

        fillable_locations = len(self.multiworld.get_locations(self.player))

        if len(itempool) < fillable_locations:
            itempool += [self.create_filler() for _ in range(fillable_locations - len(itempool))]
        elif len(itempool) > fillable_locations:
            raise Exception(
                f"{self.player_name} has {len(itempool)} items in the pool but only "
                f"{fillable_locations} fillable locations."
            )

        self.multiworld.itempool += itempool

    def set_rules(self) -> None:
        player = self.player
        starting_hero = self.options.starting_hero.current_key

        self.multiworld.completion_condition[player] = (
            lambda state: state.has("battleofevelance_victory", player, state.location_checks)
        )

        for index, region_name in enumerate(REGION_ORDER):
            required_location, entrance_items = region_entrance_requirements(region_name)
            if not required_location or not entrance_items:
                continue

            prev_region_name = REGION_ORDER[index - 1]
            source_region = self.multiworld.get_region(prev_region_name, player)
            entrance_name = f"{prev_region_name} -> {region_name}"
            entrance = self.multiworld.get_entrance(entrance_name, player)

            def entrance_rule(
                state,
                required_loc: str = required_location,
                items: Dict[str, int] = entrance_items,
                hero: str = starting_hero,
            ) -> bool:
                if not state.can_reach_location(required_loc, player):
                    return False
                for item_name, count in items.items():
                    if item_name == "ari" and hero == "ari":
                        continue
                    if item_name == "pilgrim" and hero == "pilgrim":
                        continue
                    if not state.has(item_name, player, count):
                        return False
                return True

            set_rule(entrance, entrance_rule)
            self.multiworld.register_indirect_condition(source_region, entrance)

        for location_name, requirements in build_location_item_requirements().items():
            location = self.multiworld.get_location(location_name, player)

            def location_rule(
                state,
                reqs: Dict[str, int] = requirements,
                hero: str = starting_hero,
            ) -> bool:
                for item_name, count in reqs.items():
                    if item_name == "ari" and hero == "ari":
                        continue
                    if item_name == "pilgrim" and hero == "pilgrim":
                        continue
                    if not state.has(item_name, player, count):
                        return False
                return True

            set_rule(location, location_rule)

    def fill_slot_data(self) -> Dict[str, object]:
        return {
            "starting_hero": self.options.starting_hero.current_key,
            "starting_unit": self.options.starting_unit.current_key,
            "difficulty": self.options.difficulty.value,
            "progression_difficulty": self.options.progression_difficulty.value,
            "player_color": self.options.player_color.value,
            "game_speed": self.options.game_speed.value,
        }

    def create_filler(self) -> SettlersItem:
        import random

        filler_items = [
            "starting_gold",
            "starting_clay",
            "starting_wood",
            "starting_stone",
            "starting_iron",
            "starting_sulfur",
        ]
        return self.create_item(random.choice(filler_items))
