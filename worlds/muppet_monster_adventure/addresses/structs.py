from typing import NamedTuple

from ..shared import LevelName


class PickupAddress(NamedTuple):
    """Individual pickup data is only updated whenever the game is saved, or when the player returns to the Hub."""

    active: int
    """The address of the pickup data when the level is currently active."""
    save: int
    """The address of the pickup data flag, in save data"""
    save_offset: int
    """Pickups are stored in save data as 1-2 bits. This is the offset from the start of the byte listed in `save`."""


class LevelPickupTable(NamedTuple):
    """The collection of addresses for each level's pickups.
    Note that these should be the addresses of the ACTUAL data, NOT the address
    which stores the POINTER to the data.
    These values are used at runtime to compare against the `level_last_pickup` value."""

    tokens: list[PickupAddress]


class AddressTable(NamedTuple):
    """A look-up table for all the memory addresses.
    Various parts of what we use are split across sections of memory which differ across versions.
    I felt this was cleaner than doing some shenannigans like `offset if in dynamic memory else other_offset`."""

    game_identifier: int
    """Standard PSX game identifier (SLUS_XXX.XX)"""

    loading_state: int
    """16 when the active scene/level is loaded, and 64 when currently loading"""

    active_level_name: int
    """Stores a short, ASCII identifier for the current level"""

    save_data: int
    """Current save's data in MainRAM"""

    active_save_index: int
    """Zero-based value of the active save number."""

    bosses_beaten: int
    """The index (1-based) of the **greatest** boss killed (clockwise)"""

    level_unlock_states: int
    """Each level (inc. bosses) gets 1 byte storing unlock state"""

    zone_unlocked_count: int
    """When in the Hub, how many zones (groups of 3 regular levels + boss) the player can navigate to, clockwise"""

    amulets: int
    """Bitwise flags for each amulet (morph character token) pickup"""

    power_glove: int
    """Freezing this value prevents power glove attack (tied to animation system)"""

    spin_attack: int
    """Setting this to zero prevents spin attack"""

    morphs: int
    """Bitwise flags field for the Morph powers"""

    current_lives: int
    """Current lives - signed"""

    current_health: int
    """Current HP - signed"""

    max_health: int
    """Max HP (heart containers) - signed"""

    level_state: int
    """Level energy, coin, bonus, and token count"""

    last_pickup: int
    """Stores the memory address of the last pickup"""

    level_pickup_data: dict[LevelName, LevelPickupTable]
    """Lists the memory addresses of pickups, for each level"""
