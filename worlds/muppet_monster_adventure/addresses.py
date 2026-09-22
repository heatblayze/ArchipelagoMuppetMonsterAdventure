from typing import NamedTuple


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
