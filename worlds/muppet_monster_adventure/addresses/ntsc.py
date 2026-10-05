from ..shared import LevelName
from .structs import AddressTable, LevelPickupTable, PickupAddress

ntsc_addresses = AddressTable(
    game_identifier=0x009274,
    loading_state=0x00EAB9,
    active_level_name=0x0B87F8,
    custom_save_data=0x0CCBC5,
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
                PickupAddress(active=0x01F53F4, save=0x0CCC39, save_offset=0),  # Rizzo
                PickupAddress(active=0x01F2548, save=0x0CCC26, save_offset=0),  # Bookshelves
                PickupAddress(active=0x01F52D0, save=0x0CCC38, save_offset=4),  # Smashing
                PickupAddress(active=0x01F2574, save=0x0CCC26, save_offset=2),  # Near end
                PickupAddress(active=0x01EEEC8, save=0x0CCBF5, save_offset=4),  # BONUS
            ]
        ),
        LevelName.POKER_FACES: LevelPickupTable(
            tokens=[
                PickupAddress(active=0x01F87BC, save=0x0CCC94, save_offset=4),  # Targets
                PickupAddress(active=0x01F69B8, save=0x0CCC8A, save_offset=6),  # Pillar
                PickupAddress(active=0x01F86A8, save=0x0CCC94, save_offset=0),  # Blocks
                PickupAddress(active=0x01F69E4, save=0x0CCC8B, save_offset=0),  # Rooftop
                PickupAddress(active=0x01F3724, save=0x0CCC5D, save_offset=4),  # BONUS
            ]
        ),
        LevelName.GRAVE_MATTERS: LevelPickupTable(
            tokens=[
                PickupAddress(active=0x01F3C28, save=0x0CCD6D, save_offset=0),  # Rizzo
                PickupAddress(active=0x01F0FDC, save=0x0CCD5A, save_offset=2),  # On pillar near Rizzo
                PickupAddress(active=0x01F41E4, save=0x0CCD6F, save_offset=0),  # Memory minigame
                PickupAddress(active=0x01F1008, save=0x0CCD5A, save_offset=4),  # Tunnel
                PickupAddress(active=0x01ED850, save=0x0CCD2C, save_offset=4),  # BONUS
            ]
        ),
        LevelName.MOLTEN_MAYHEM: LevelPickupTable(
            tokens=[
                PickupAddress(active=0x01FB85C, save=0x0CCDDE, save_offset=4),  # Target shooting
                PickupAddress(active=0x01FB660, save=0x0CCDDD, save_offset=6),  # Ghost hunt
                PickupAddress(active=0x01F6D04, save=0x0CCDC0, save_offset=0),  # Wall walk
                PickupAddress(active=0x01F6CD8, save=0x0CCDBF, save_offset=6),  # Hidden room
                PickupAddress(active=0x01F3CBC, save=0x0CCD94, save_offset=4),  # BONUS
            ]
        ),
        LevelName.SHIVERING_TIMBER_SHOALS: LevelPickupTable(
            tokens=[
                PickupAddress(active=0x01DCDC0, save=0x0CCE4D, save_offset=4),  # Shells
                PickupAddress(active=0x01D741C, save=0x0CCE28, save_offset=2),  # Behind smash wall
                PickupAddress(active=0x01D7448, save=0x0CCE28, save_offset=4),  # Super jump pad
                PickupAddress(active=0x01DAA10, save=0x0CCE3F, save_offset=6),  # Race Simon
                PickupAddress(active=0x01D4348, save=0x0CCDFC, save_offset=4),  # BONUS
            ]
        ),
        LevelName.HIKE_OF_THE_HAUNTED: LevelPickupTable(
            tokens=[
                PickupAddress(active=0x01E6234, save=0x0CCEF8, save_offset=0),  # Big tree
                PickupAddress(active=0x01E6208, save=0x0CCEF7, save_offset=6),  # Jump pads
                PickupAddress(active=0x01E9C28, save=0x0CCF0E, save_offset=6),  # Totem shooting
                PickupAddress(active=0x01EB824, save=0x0CCF16, save_offset=2),  # Gliding game
                PickupAddress(active=0x01E61DC, save=0x0CCEF7, save_offset=4),  # Near gliding game
                PickupAddress(active=0x01E324C, save=0x0CCECC, save_offset=4),  # BONUS
            ]
        ),
    },
)
