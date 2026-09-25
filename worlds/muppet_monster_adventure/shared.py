from enum import Flag, StrEnum, auto

base_id: int = 25_899_560
game_name: str = "Muppet Monster Adventure"


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
def any_weapon_flag(other: AbilityFlag) -> list[AbilityFlag]:
    return [
        other | AbilityFlag.GLOVE,
        other | AbilityFlag.SPIN,
    ]


class LevelName(StrEnum):
    HUB = "Hub"
    PEACOCK_PURGATORY = "Peacock Purgatory"
    HALLWAYS_OF_DOOM = "Hallways of Doom"
    POKER_FACES = "Poker Faces"
    NOSEFERATU = "Noseferatu"


whitelisted_starting_levels: list[LevelName] = [
    LevelName.PEACOCK_PURGATORY,
    LevelName.HALLWAYS_OF_DOOM,
    LevelName.POKER_FACES,
]


class FillerType(StrEnum):
    GAIN_HEALTH = "Gain Health"
    GAIN_HEART = "Fly Heart"
    GAIN_LIFE = "Extra Life"


class TrapType(StrEnum):
    LOSE_HEALTH = "Ouch!"
    LOSE_HEART = "Fly Away"
    LOSE_LIFE = "No Life Gaming"


class LevelConfigurationException(Exception):
    """Exception raised when a level has been configured incorrectly."""

    def __init__(self, name: LevelName, message: str):
        super().__init__(f"Level '{name}' has been configured incorrectly: {message}")
