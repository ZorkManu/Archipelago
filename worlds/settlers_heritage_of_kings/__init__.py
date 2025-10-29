from typing import Dict, List
from BaseClasses import Tutorial, MultiWorld, Region, ItemClassification
from worlds.AutoWorld import World, WebWorld
from worlds.generic.Rules import set_rule
from .Options import SettlersGameOptions
from .Items import SettlersItem, item_table
from .Locations import SettlersLocation, location_table

class SettlersWeb(WebWorld):
    theme = "stone"

    setup = Tutorial(
        "Multiworld Setup Guide",
        "A guide to setting up the Archipelago Settlers client on your computer.",
        "English",
        "setup_en.md",
        authors=["ZorkManu"],
        link="coming soon"
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
    location_name_to_id = {location: data.address for location, data in location_table.items()}
    item_name_to_id = {name: data.code for name, data in item_table.items()}

    data_version = 1

    def create_regions(self):
        # Create regions.
        menu_region = Region("Menu", self.player, self.multiworld)
        self.multiworld.regions.append(menu_region)  # or use += [menu_region...]

        game_region = Region("Game", self.player, self.multiworld)
        game_region.add_locations(self.location_name_to_id, SettlersLocation)

        self.multiworld.regions.append(game_region)

        menu_region.connect(game_region)

    def create_item(self, name: str, filler: bool = 0) -> SettlersItem:
        """Creates a SettlersItem with the given name."""
        item_data = item_table[name]
        return SettlersItem(name=name, code=item_data.code, player=self.player, classification=item_data.type)

    
    def create_event(self, event: str) -> SettlersItem:
        return SettlersItem(name=event, classification=ItemClassification.progression, code=None, player=self.player)

    def create_items(self) -> None:
        """Creates the items for the game"""
        starting_items: List[SettlersItem] = []
        
        self.multiworld.push_precollected(self.create_item(self.options.starting_hero.current_key))
        
        # Add the starting unit if selected
        if self.options.starting_unit != "disabled":
            unit_name = f"progressive_{self.options.starting_unit.current_key}"
            if unit_name in self.item_name_to_id:
                self.multiworld.push_precollected(self.create_item(unit_name))
                starting_items.append(unit_name)

        for item in map(self.create_item, item_table.keys()):
            if item not in starting_items:
                for i in range(item_table[item.name].quantity):
                    self.multiworld.itempool.append(item)

        total_locations = len(self.multiworld.get_unfilled_locations(self.player))

        for _ in range(total_locations - len(self.multiworld.itempool)):
            self.multiworld.itempool.append(self.create_filler())

    def set_rules(self):
        """Sets the rules for accessing locations"""
        # Set the completion condition
        self.multiworld.get_location("battleofevelance_victory", self.player).place_locked_item(self.create_event("Victory"))

        self.multiworld.completion_condition[self.player] = lambda state: state.has("Victory", self.player)

    def fill_slot_data(self) -> Dict[str, any]:
        """Fills the slot data for the client"""
        return {
            "starting_hero": self.options.starting_hero.current_key,
            "starting_unit": self.options.starting_unit.current_key,
            "difficulty": self.options.difficulty.value,
            "progression_difficulty": self.options.progression_difficulty.value,
            "player_color": self.options.player_color.value,
        }

    def create_filler(self) -> SettlersItem:
        """Creates a random filler item from the available options."""
        import random
        filler_items = [
            "starting_gold",
            "starting_clay",
            "starting_wood",
            "starting_stone",
            "starting_iron",
            "starting_sulfur",
            "additional_attraction",
            "additional_motivation",
        ]
        return self.create_item(random.choice(filler_items))