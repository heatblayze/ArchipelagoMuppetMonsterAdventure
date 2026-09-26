from ..shared import LevelName
from .structs import AddressTable, LevelPickupTable, PickupAddress

ntsc_addresses = AddressTable(
    game_identifier=0x009274,
    loading_state=0x00EAB9,
    active_level_name=0x0B87F8,
    save_data=0x0,
    active_save_index=0x0CCAE8,
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
        LevelName.PEACOCK_PURGATORY: LevelPickupTable(
            tokens=[
                PickupAddress(active=0x01F2964, save=0x0CCBB9, save_offset=2),  # Near exit
                PickupAddress(active=0x01F2938, save=0x0CCBB9, save_offset=0),  # Super jump pad
                PickupAddress(active=0x01F4678, save=0x0CCBC3, save_offset=4),  # Percy
                PickupAddress(active=0x01F66C0, save=0x0CCBD0, save_offset=4),  # Sunflower game
                PickupAddress(active=0x01EF998, save=0x0CCB8F, save_offset=4),  # Bonus
            ]
        ),
        LevelName.HALLWAYS_OF_DOOM: LevelPickupTable(
            tokens=[
                PickupAddress(active=0x01F53F4, save=0x0, save_offset=0),
                PickupAddress(active=0x01F2548, save=0x0, save_offset=0),
                PickupAddress(active=0x01F52D0, save=0x0, save_offset=0),
                PickupAddress(active=0x01F2574, save=0x0, save_offset=0),
                PickupAddress(active=0x01EEEC8, save=0x0, save_offset=0),
            ]
        ),
        LevelName.POKER_FACES: LevelPickupTable(
            tokens=[
                PickupAddress(active=0x01F87BC, save=0x0, save_offset=0),
                PickupAddress(active=0x01F69B8, save=0x0, save_offset=0),
                PickupAddress(active=0x01F86A8, save=0x0, save_offset=0),
                PickupAddress(active=0x01F69E4, save=0x0, save_offset=0),
                PickupAddress(active=0x01F3724, save=0x0, save_offset=0),
            ]
        ),
    },
)
