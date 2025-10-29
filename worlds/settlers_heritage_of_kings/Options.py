from dataclasses import dataclass
from Options import Choice, PerGameCommonOptions

class StartingHero(Choice):
    """Sets the starting hero for the game. Dario has 1 of 3 Stages"""
    display_name = "Starting Hero"
    option_progressive_dario = 1
    option_erec = 2
    option_helias = 3
    option_ari = 4
    option_pilgrim = 5
    option_salim = 6
    option_kerberos = 7
    option_mary = 8
    option_varg = 9
    option_yuki = 10
    option_drake = 11
    option_kala = 12
    option_random = 13
    default = 13

class StartingUnit(Choice):
    """Sets the starting unit for the game."""
    display_name = "Starting Unit"
    option_disabled = 1
    option_sword = 2
    option_bow = 3
    option_spear = 4
    option_heavy_cavalry = 5
    option_light_cavalry = 6
    option_cannon = 7
    option_rifle = 8
    option_scout = 9
    option_thief = 10
    option_random = 11
    default = 11

class Difficulty(Choice):
    """Sets the difficulty for the game."""
    display_name = "Difficulty"
    option_normal = 1
    option_hard = 2
    option_extreme = 3
    default = 1

class PlayerColor(Choice):
    """Sets the Player Color. Some Colors will be used by enemies/allies (red,purple are common enemy colors)"""
    display_name = "Player Color"
    option_blue = 1
    option_red = 2
    option_yellow = 3
    option_turquoise = 4
    option_orange = 5
    option_purple = 6
    option_pink = 7
    option_lime = 8
    option_green = 9
    option_white = 13
    default = 1

class ProgressionDifficulty(Choice):
    """If enabled increases the difficulty if more items are collected."""
    display_name = "Progression Difficulty"
    option_true = 1
    option_false = 0

class GameSpeed(Choice):
    """Sets the Game Speed (normal recommended)"""
    display_name = "Game Speed"
    option_slow = 1
    option_normal = 2
    option_fast = 3

@dataclass
class SettlersGameOptions(PerGameCommonOptions):
    starting_hero: StartingHero
    starting_unit: StartingUnit
    difficulty: Difficulty
    progression_difficulty: ProgressionDifficulty
    player_color: PlayerColor
    game_speed = GameSpeed