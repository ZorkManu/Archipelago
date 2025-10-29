from typing import Dict, NamedTuple
from BaseClasses import Item, ItemClassification

class SettlersItem(Item):
    game = "SettlersHeritageOfKings"

class SettlersItemData(NamedTuple):
    code: int
    name: str
    type: ItemClassification = ItemClassification.filler
    quantity: int = 1

item_table = {
    "better_chassis": SettlersItemData(code=100, name="Better Chassis", type=ItemClassification.useful),
    "better_training_archery": SettlersItemData(code=101, name="Better Training Archery", type=ItemClassification.useful),
    "better_training_barracks": SettlersItemData(code=102, name="Better Training Barracks", type=ItemClassification.useful),
    "shoeing": SettlersItemData(code=103, name="Shoeing", type=ItemClassification.useful),
    "enable_militia": SettlersItemData(code=104, name="Enable Militia"),
    "masonry": SettlersItemData(code=105, name="Masonry", type=ItemClassification.useful),
    "tracking": SettlersItemData(code=106, name="Tracking"),

    "progressive_math": SettlersItemData(code=107, name="Progressive Math", type=ItemClassification.progression, quantity=4),
    "progressive_construction": SettlersItemData(code=108, name="Progressive Construction", type=ItemClassification.progression, quantity=4),
    "progressive_alchemy": SettlersItemData(code=109, name="Progressive Alchemy", type=ItemClassification.progression, quantity=4),
    "progressive_mercenaries": SettlersItemData(code=110, name="Progressive Mercenaries", type=ItemClassification.progression, quantity=4),
    "progressive_literacy": SettlersItemData(code=111, name="Progressive Literacy", type=ItemClassification.progression, quantity=4),

    "progressive_sword": SettlersItemData(code=112, name="Progressive Sword", type=ItemClassification.progression, quantity=4),
    "progressive_bow": SettlersItemData(code=113, name="Progressive Bow", type=ItemClassification.progression, quantity=4),
    "progressive_spear": SettlersItemData(code=114, name="Progressive Spear", type=ItemClassification.progression, quantity=4),
    "progressive_heavy_cavalry": SettlersItemData(code=115, name="Progressive Heavy Cavalry", type=ItemClassification.progression, quantity=2),
    "progressive_light_cavalry": SettlersItemData(code=116, name="Progressive Light Cavalry", type=ItemClassification.progression, quantity=2),
    "progressive_cannon": SettlersItemData(code=117, name="Progressive Cannon", type=ItemClassification.progression, quantity=4),
    "progressive_rifle": SettlersItemData(code=118, name="Progressive Rifle", type=ItemClassification.progression, quantity=2),
    "progressive_scout": SettlersItemData(code=119, name="Progressive Scout", quantity=3),
    "progressive_thief": SettlersItemData(code=120, name="Progressive Thief", type=ItemClassification.progression, quantity=2),

    "progressive_heavy_armor": SettlersItemData(code=121, name="Progressive Heavy Armor", type=ItemClassification.useful, quantity=3),
    "progressive_light_armor": SettlersItemData(code=122, name="Progressive Light Armor", type=ItemClassification.useful, quantity=3),
    "progressive_fleece_armor": SettlersItemData(code=123, name="Progressive Fleece Armor", type=ItemClassification.useful, quantity=2),
    "progressive_sword_damage": SettlersItemData(code=124, name="Progressive Sword Damage", type=ItemClassification.useful, quantity=2),
    "progressive_bow_damage": SettlersItemData(code=125, name="Progressive Bow Damage", type=ItemClassification.useful, quantity=2),
    "progressive_spear_damage": SettlersItemData(code=126, name="Progressive Spear Damage", type=ItemClassification.useful, quantity=2),
    "progressive_cannon_damage": SettlersItemData(code=127, name="Progressive Cannon Damage", type=ItemClassification.useful, quantity=2),
    "progressive_rifle_damage": SettlersItemData(code=128, name="Progressive Rifle Damage", type=ItemClassification.useful, quantity=2),

    "progressive_weathertech": SettlersItemData(code=129, name="Progressive Weathertech", type=ItemClassification.progression, quantity=2),
    "progressive_village_center": SettlersItemData(code=130, name="Progressive Village Center", quantity=3),

    "progressive_dario": SettlersItemData(code=131, name="Progressive Dario", type=ItemClassification.progression, quantity=3),
    "erec": SettlersItemData(code=132, name="Erec", type=ItemClassification.useful),
    "helias": SettlersItemData(code=133, name="Helias", type=ItemClassification.progression),
    "ari": SettlersItemData(code=134, name="Ari", type=ItemClassification.progression),
    "pilgrim": SettlersItemData(code=135, name="Pilgrim", type=ItemClassification.progression),
    "salim": SettlersItemData(code=136, name="Salim", type=ItemClassification.useful),
    "kerberos": SettlersItemData(code=137, name="Kerberos", type=ItemClassification.useful),
    "mary": SettlersItemData(code=138, name="Mary", type=ItemClassification.useful),
    "varg": SettlersItemData(code=139, name="Varg", type=ItemClassification.useful),
    "yuki": SettlersItemData(code=140, name="Yuki", type=ItemClassification.useful),
    "drake": SettlersItemData(code=141, name="Drake", type=ItemClassification.useful),
    "kala": SettlersItemData(code=142, name="Kala", type=ItemClassification.useful),

    "starting_gold": SettlersItemData(code=143, name="Starting Gold"),
    "starting_clay": SettlersItemData(code=144, name="Starting Clay"),
    "starting_wood": SettlersItemData(code=145, name="Starting Wood"),
    "starting_stone": SettlersItemData(code=146, name="Starting Stone"),
    "starting_iron": SettlersItemData(code=147, name="Starting Iron"),
    "starting_sulfur": SettlersItemData(code=148, name="Starting Sulfur"),
    "additional_attraction": SettlersItemData(code=149, name="Additional Attraction"),
    "additional_motivation": SettlersItemData(code=150, name="Additional Motivation"),
}