from enum import StrEnum
from typing import NamedTuple


# TODO: fill out
class AddressType(StrEnum):
    LOADING_STATE = "Loading State"  # 16 on ready, 64 when loading
    BOSSES_BEATEN = (
        "Bosses Beaten"  # An awesome field that lists the highest boss number beaten (please find an alternative)
    )
    LEVEL_STATE = "Level State"  # Energy, tokens, bonus (per level)
    AMULETS = "Amulets"  # All amulets are one 3-byte long field
    POWER_GLOVE = "Power Glove"
    SPIN_ATTACK = "Spin Attack"
    MORPHS = "Morphs"  # This is also a single 1-byte field


# A look-up table for all the memory addresses.
# Various parts of what we use are split across sections of memory which differ across versions.
# I felt this was cleaner than doing some shenannigans like `offset if in dynamic memory else other_offset`.
class AddressTable(NamedTuple):
    loading_state: int
    active_level_name: int
    bosses_beaten: int
    level_state_start: int  # presumably these are all in uniform blocks, so we only need the start
    level_unlock_start: int
    zones_unlocked: int
    amulets: int
    power_glove: int
    spin_attack: int
    morphs: int
