from enum import Flag, StrEnum, auto

base_id: int = 25_899_560
game_name: str = "Muppet Monster Adventure"


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


class ItemFlag(Flag):
    GAIN_HEALTH = auto(),
    GAIN_HEART  = auto(),
    GAIN_LIFE   = auto(),


class TrapFlag(Flag):
    LOSE_HEALTH = auto(),
    LOSE_HEART  = auto(),
    LOSE_LIFE   = auto(),
