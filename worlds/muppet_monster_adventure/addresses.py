from typing import NamedTuple


# A look-up table for all the memory addresses.
# Various parts of what we use are split across sections of memory which differ across versions.
# I felt this was cleaner than doing some shenannigans like `offset if in dynamic memory else other_offset`.
class AddressTable(NamedTuple):
    game_identifier: int
    loading_state: int
    active_level_name: int
    bosses_beaten: int
    level_state_start: int  # presumably these are all in uniform blocks, so we only need the start
    level_unlock_flags: int
    zone_unlocked_count: int
    amulets: int
    power_glove: int
    spin_attack: int
    morphs: int
    current_lives: int
    current_health: int
    max_health: int


game_version_addresses: dict[str, AddressTable] = {
    "SLUS_012.38": AddressTable(
        game_identifier=0x009274,
        loading_state=0x00EAB9,
        active_level_name=0x0B87F8,
        bosses_beaten=0x0B8904,
        # TODO: this is kinda wrong, since it starts after some data we don't care about.
        # We should update this to include said data, and then just ignore it.
        level_state_start=0x0CCB86,
        level_unlock_flags=0x0AA0C4,
        zone_unlocked_count=0x0E22F0,
        amulets=0x0CCB78,
        power_glove=0x0B8408,
        spin_attack=0x0B7BEF,
        morphs=0x0B76F8,
        current_lives=0x0B8908,
        current_health=0x0B8909,
        max_health=0x0B890A,
    ),
}
