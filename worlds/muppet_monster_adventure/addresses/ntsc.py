from ..shared import LevelName
from .structs import AddressTable, PickupAddresses

ntsc_addresses = AddressTable(
    game_identifier=0x009274,
    loading_state=0x00EAB9,
    active_level_name=0x0B87F8,
    bosses_beaten=0x0B8904,
    level_unlock_states=0x0AA0C4,
    zone_unlocked_count=0x0E22F0,
    amulets=0x0CCB78,
    power_glove=0x0B8408,
    spin_attack=0x0B7BEF,
    morphs=0x0B76F8,
    current_lives=0x0B8908,
    current_health=0x0B8909,
    max_health=0x0B890A,
    # TODO: this is kinda wrong, since it starts after some data we don't care about.
    # We should update this to include said data, and then just ignore it.
    level_state=0x0CCB86,
    last_pickup=0x0B8698,
    level_pickup_data={
        LevelName.PEACOCK_PURGATORY: PickupAddresses(
            tokens=[
                0x01F2964,
                0x01F2938,
                0x01F4678,
                0x01F66C0,
                0x01EF998,
            ]
        ),
        LevelName.HALLWAYS_OF_DOOM: PickupAddresses(
            tokens=[
                0x01F53F4,
                0x01F2548,
                0x01F52D0,
                0x01F2574,
                0x01EEEC8,
            ]
        ),
        LevelName.POKER_FACES: PickupAddresses(
            tokens=[
                0x01F87BC,
                0x01F69B8,
                0x01F86A8,
                0x01F69E4,
                0x01F3724,
            ]
        ),
    },
)
