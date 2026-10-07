from enum import Flag, StrEnum, auto

base_id: int = 25_899_560
game_name: str = "Muppet Monster Adventure"


class AmuletType(StrEnum):
    NOSEFERATU_AMULET = "Noseferatu Amulet"
    WEREBEAR_AMULET = "Werebear Amulet"
    KER_MONSTER_AMULET = "Ker-monster Amulet"
    MUCK_MONSTER_AMULET = "Muck Monster Amulet"
    GHOUL_FRIEND_AMULET = "Ghoul-friend Amulet"


# Flag because this is used for logic
class AbilityFlag(Flag):
    GLIDE = auto()
    CLIMB = auto()
    PUSH = auto()
    SWIM = auto()
    SMASH = auto()
    GLOVE = auto()
    SPIN = auto()
    ALL_MORPHS = GLIDE | CLIMB | PUSH | SWIM | SMASH
    ALL_WEAPONS = GLOVE | SPIN


# Helper function to generate location rules that just require being able to kill enemies.
def any_weapon_flag(other: AbilityFlag | None = None) -> list[AbilityFlag]:
    if other is None:
        return [AbilityFlag.GLOVE, AbilityFlag.SPIN]
    return flag_variants(other, AbilityFlag.GLOVE, AbilityFlag.SPIN)


def flag_variants(shared_reqs: AbilityFlag, *other: AbilityFlag) -> list[AbilityFlag]:
    """
    Helper function to generate location rules combining multiple variations of a single base rule.
    Usage: (sharedFlag1 | sharedFlag2 | sharedFlag3, variant1, variant2, etc.)
    """
    args: list[AbilityFlag] = list(other)
    return [shared_reqs | other_item for other_item in args]


class LevelName(StrEnum):
    HUB = "Hub"
    PEACOCK_PURGATORY = "Peacock Purgatory"
    HALLWAYS_OF_DOOM = "Hallways of Doom"
    POKER_FACES = "Poker Faces"
    NOSEFERATU_BITES_BACK = "Noseferatu Bites Back!"
    GRAVE_MATTERS = "Grave Matters"
    MOLTEN_MAYHEM = "Molten Mayhem"
    SHIVERING_TIMBER_SHOALS = "Shivering Timber Shoals"
    BEE_WARE_THE_WEREBEAR = "Bee-ware the WereBear!"
    HIKE_OF_THE_HAUNTED = "Hike of the Haunted"
    THE_RIVER_VILE = "The River Vile"
    ESCAPE_CLAWS = "Escape Claws"
    COWER_BEFORE_KER_MONSTER = "Cower Before... Ker-Monster!"
    CROAK_LAHOMA = "Croak-Lahoma"
    ARABIAN_FRIGHTS = "Arabian Frights"
    FEELING_FLUSHED = "Feeling Flushed"
    THE_MUCK_MONSTER_SLIMETH = "The Muck Monster Slimeth"


# These are levels wherein you can always get at least one check with nothing.
whitelisted_starting_levels: list[LevelName] = [
    LevelName.PEACOCK_PURGATORY,
    LevelName.HALLWAYS_OF_DOOM,
    LevelName.POKER_FACES,
]


class FillerType(StrEnum):
    GAIN_HEALTH = "Yip Yip Yip"
    GAIN_HEART = "Delicious Cookie! Om nom nom"
    GAIN_LIFE = "Kissy Kissy"


class TrapType(StrEnum):
    LOSE_HEALTH = "Heckled by Statler and Waldorf"
    LOSE_HEART = "Bunsen's Failed Experiment"
    LOSE_LIFE = "Maniacal Laugh"


class LevelConfigurationException(Exception):
    """Exception raised when a level has been configured incorrectly."""

    def __init__(self, name: LevelName, message: str):
        super().__init__(f"Level '{name}' has been configured incorrectly: {message}")
