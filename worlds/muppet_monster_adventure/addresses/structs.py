from typing import NamedTuple

from worlds.muppet_monster_adventure.shared import LevelName


class TokenAddresses(NamedTuple):
    token_1: int
    token_2: int
    token_3: int
    token_4: int
    token_5: int | None = None


# A look-up table for all the memory addresses.
# Various parts of what we use are split across sections of memory which differ across versions.
# I felt this was cleaner than doing some shenannigans like `offset if in dynamic memory else other_offset`.
class AddressTable(NamedTuple):
    game_identifier: int
    loading_state: int
    active_level_name: int
    bosses_beaten: int
    level_unlock_flags: int
    zone_unlocked_count: int
    amulets: int
    power_glove: int
    spin_attack: int
    morphs: int
    current_lives: int
    current_health: int
    max_health: int
    level_state_start: int  # presumably these are all in uniform blocks, so we only need the start
    level_token_data: dict[LevelName, TokenAddresses]
