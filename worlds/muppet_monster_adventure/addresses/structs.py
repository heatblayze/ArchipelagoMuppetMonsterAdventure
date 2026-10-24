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

class MiniGameAddress(NamedTuple):
    """Mini-games have a Retry message address and a Start message address."""

    retry: int
    """The address of the mini-game message that displays when a mini-game is retried."""
    start: int
    """The address of the mini-game message that displays when talking with Pepe the first time"""
    name: str
    """The name of the mini-game"""


class LevelPickupTable(NamedTuple):
    """The collection of addresses for each level's pickups.
    Note that these should be the addresses of the ACTUAL data, NOT the address
    which stores the POINTER to the data.
    These values are used at runtime to compare against the `level_last_pickup` value."""

    tokens: list[PickupAddress]

class MiniGameTable(NamedTuple):
    """The collection of addresses for each level's mini-game.
    Note that these should be the addresses of the ACTUAL data, NOT the address
    which stores the POINTER to the data.
    These values are used at runtime to compare against the `pepe_message_message_pointer` address."""

    minigames: list[MiniGameAddress]


class AddressTable(NamedTuple):
    """A look-up table for all the memory addresses.
    Various parts of what we use are split across sections of memory which differ across versions.
    I felt this was cleaner than doing some shenannigans like `offset if in dynamic memory else other_offset`."""

    # This is number of Frames per second, not a Memory Address
    game_timer_frames: int
    """The physics/timer seems to be different to the game timer (60fps for NTSC, 50fps for PAL)"""

    game_identifier: int
    """Standard PSX game identifier (SLUS_XXX.XX)"""

    loading_state: int
    """16 when the active scene/level is loaded, and 64 when currently loading"""

    active_level_name: int
    """Stores a short, ASCII identifier for the current level"""

    custom_save_data: int
    """Current save's custom storage data in MainRAM"""

    active_save_index: int
    """Zero-based value of the active save number"""

    pepe_message_ui_counter: int
    """Timer, or counter, for the Pepe UI element"""

    pepe_message_ui_pointer: int
    """Seems to be the pointer for the UI itself"""

    pepe_message_message_pointer: int
    """Pointer to the message being loaded"""

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

    chicken_timer: int
    """Timer for the Chicken Gun (4 bytes) - signed"""

    level_pickup_data: dict[LevelName, LevelPickupTable]
    """Lists the memory addresses of pickups, for each level"""

    level_hub_message:int
    """The memory address for the Hub message"""

    level_minigame_data: dict[LevelName, MiniGameTable]
    """Lists the memory addresses of mini-games, for each level"""

    # Location of cheat pieces in the menu, these need to be cleared every frame
    cheat_menu_level_select: int
    """Makes a new option appear in the opening menu"""

    cheat_permanent_level_unlock: int
    """Makes all levels permanently unlocked"""

    cheat_permanent_morph_unlock: int
    """Doesn't seem to work, but is implied to make all Morphs permanently unlocked"""

    always_access_hub: list[int]
    """Memory locations of instructions to edit which allows the player to always access the Hub"""

    hub_autospin: int
    """Memory address of the instruction which triggers the auto-spin in the Hub when you select a locked level"""
