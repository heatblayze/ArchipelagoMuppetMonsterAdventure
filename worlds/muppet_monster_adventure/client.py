from math import ceil, floor
from typing import TYPE_CHECKING, ClassVar, Sequence

from .addresses.ntsc import ntsc_addresses
from .addresses.structs import AddressTable, LevelPickupTable

if TYPE_CHECKING:
    from worlds._bizhawk.context import BizHawkClientContext

import worlds._bizhawk as bizhawk
from NetUtils import ClientStatus
from worlds._bizhawk.client import BizHawkClient

from .items import MMAAbilityItemData, MMAFillerItemData, MMALevelItemData, MMATrapItemData, item_id_to_item
from .locations import (
    LocationType,
    MMALocationData,
    MMARegion,
    location_name_to_id,
    location_type_lookup,
    location_type_lookup_by_region,
    non_boss_region_lookup,
    region_lookup,
)
from .shared import AbilityFlag, FillerType, LevelConfigurationException, LevelName, TrapType, game_name


class MMAAddressTableConsumer:
    def __init__(self, address_table: AddressTable) -> None:
        self.address_table: AddressTable = address_table
        pass


class MMAFlagField:
    def __init__(self, size: int, offset: int) -> None:
        self.size: int = size
        self.offset: int = offset
        self.flags: list[bool] = [False] * size

    def split_flags(self, data: int) -> list[bool]:
        new_flags: list[bool] = [False] * self.size
        for i in range(self.size):
            new_flags[i] = ((data >> self.offset + i) & 1) == 1
        return new_flags

    def check(self, data: int) -> list[int]:
        new_flags = self.split_flags(data)
        changes: list[int] = []
        for i in range(self.size):
            if new_flags[i] and new_flags[i] != self.flags[i]:
                changes.append(i)
                self.flags[i] = True
        return changes


class MMAMorphState:
    packed_size: int = 5

    def __init__(self) -> None:
        self.glide: bool = False
        self.climb: bool = False
        self.push: bool = False
        self.swim: bool = False
        self.smash: bool = False

    def unpack(self, packed_data: int) -> None:
        self.glide = ((packed_data >> 0) & 1) == 1
        self.climb = ((packed_data >> 1) & 1) == 1
        self.push = ((packed_data >> 2) & 1) == 1
        self.swim = ((packed_data >> 3) & 1) == 1
        self.smash = ((packed_data >> 4) & 1) == 1

    def pack(self) -> int:
        return (self.glide << 0) | (self.climb << 1) | (self.push << 2) | (self.swim << 3) | (self.smash << 4)

    def get_bytes(self) -> bytes:
        return self.pack().to_bytes(2, "little")


class MMALevelState(MMAAddressTableConsumer):
    level_state_total_size: int = 104
    level_state_relevant_size: int = 6
    last_pickup_size: int = 3
    token_active_offset: int = 3  # Num bytes after address where active flag is stored

    bonus_offset: int = 0
    energy_offset: int = 2
    energy_size: int = 2

    def __init__(
        self,
        address_table: AddressTable,
        region: MMARegion,
        state_address: int,
        energy_thresholds: list[float],
    ) -> None:
        super().__init__(address_table)
        self.region: MMARegion = region
        self.state_address: int = state_address
        self.energy_thresholds: list[float] = energy_thresholds
        self.max_energy: int = self.region.energy_count
        self.location_lookup: dict[LocationType, list[MMALocationData]] = location_type_lookup_by_region[
            self.region.name
        ]
        self.pickup_table: LevelPickupTable = self.address_table.level_pickup_data[LevelName(self.region.name)]

        # State
        self.bonus: MMAFlagField = MMAFlagField(size=5, offset=0)
        self.energy: int = 0
        self.current_energy_threshold: int = -1
        self.last_pickup_addr: int = 0
        self.collected_tokens: list[bool] = [False] * 5

        # Validation
        if len(self.location_lookup[LocationType.ENERGY]) != len(self.energy_thresholds):
            raise LevelConfigurationException(
                LevelName(self.region.name),
                f"Client expects {len(self.energy_thresholds)} but the level has {len(self.location_lookup[LocationType.ENERGY])}",
            )

    def print(self) -> str:
        return f"Tokens: {self.collected_tokens}, Energy: {self.energy}, Bonus: {self.bonus.flags}"

    # TODO: Need a method to validate all of this data on connect,
    # since the game stores all permanent pickups just after the level's general data.
    # It should include a param indicating whether this is the active level, since persisted level
    # data is only updated when the player returns to the Hub.
    async def get_checked_locations(self, ctx: "BizHawkClientContext") -> list[int]:
        # TODO: technically we could do visit-sanity if we wanted, since the game tracks it.
        # Would need to adjust all of this though, since it's 2 bytes prior to the Bonus.
        data = await bizhawk.read(
            ctx.bizhawk_ctx,
            [
                (self.state_address, self.level_state_relevant_size, "MainRAM"),
                (self.address_table.last_pickup, self.last_pickup_size, "MainRAM"),
            ],
        )
        state_data = data[0]
        last_pickup = int.from_bytes(data[1], byteorder="little")

        bonus_changes = self.bonus.check(state_data[self.bonus_offset])  # Single byte order doesn't matter
        updated_energy = int.from_bytes(
            state_data[self.energy_offset : self.energy_offset + self.energy_size], byteorder="little"
        )

        collected_locations: list[int] = []
        if len(bonus_changes) > 0:
            bonus_location_lookup = self.location_lookup[LocationType.BONUS]
            collected_locations.extend([bonus_location_lookup[idx].ap_id() for idx in bonus_changes])

        if updated_energy > self.energy:
            self.energy = updated_energy
            if self.current_energy_threshold + 1 < len(self.energy_thresholds):
                energy_location_lookup = self.location_lookup[LocationType.ENERGY]
                for i in range(self.current_energy_threshold + 1, len(self.energy_thresholds)):
                    # Floor to ensure there's no weird edge-cases with the floats
                    target = floor(self.energy_thresholds[i] * self.max_energy)
                    if self.energy >= target:
                        collected_locations.append(energy_location_lookup[i].ap_id())
                        self.current_energy_threshold = i

        if last_pickup != self.last_pickup_addr:
            self.last_pickup_addr = last_pickup
            token_location_lookup = self.location_lookup[LocationType.TOKEN]
            for i, token_info in enumerate(self.pickup_table.tokens):
                if self.last_pickup_addr == token_info.active:
                    self.collected_tokens[i]
                    collected_locations.append(token_location_lookup[i].ap_id())
                    break
        return collected_locations

    async def initialize(self, ctx: "BizHawkClientContext", active: bool) -> list[int]:
        from CommonClient import logger

        """Returns any checked locations from save data.
        If the level is currently active it instead checks the active memory."""
        # We only need to check pickups - all other data is checked via check_locations
        collected_locations: list[int] = []
        token_location_lookup = self.location_lookup[LocationType.TOKEN]
        token_addresses: list[tuple[int, int, str]] = [
            (token.active + self.token_active_offset, 1, "MainRAM") if active else (token.save, 1, "MainRAM")
            for token in self.pickup_table.tokens
        ]
        addresses = await bizhawk.read(ctx.bizhawk_ctx, token_addresses)
        for i, token in enumerate(self.pickup_table.tokens):
            if (active and token.active == 0) or (not active and token.save == 0):
                continue
            if active:
                if addresses[i][0] == 0:
                    self.collected_tokens[i]
                    collected_locations.append(token_location_lookup[i].ap_id())
                    logger.info(f"Collected token from active level {token_location_lookup[i].full_identifier}")
            else:
                if ((addresses[i][0] >> token.save_offset) & 1) == 1:
                    self.collected_tokens[i]
                    collected_locations.append(token_location_lookup[i].ap_id())
                    logger.info(f"Collected token from save state {token_location_lookup[i].full_identifier}")
        return collected_locations


class MMAAmuletState:
    # TODO: maybe provide item identifier list
    def __init__(self, offset: int) -> None:
        self.flags: MMAFlagField = MMAFlagField(4, offset)

    # TODO: this should return location ids
    def get_checked_locations(self, data: int) -> list[int]:
        return self.flags.check(data)


class MMAPlayerState(MMAAddressTableConsumer):
    # Limit the maximum health and lives to this number
    max_limit: int = 100

    packed_size: int = MMAMorphState.packed_size + 2

    def __init__(self, address_table: AddressTable) -> None:
        super().__init__(address_table)
        self.morphs: MMAMorphState = MMAMorphState()
        self.glove: bool = False
        self.spin: bool = False

    def unpack(self, packed_data: int) -> None:
        self.morphs.unpack(packed_data)
        self.glove = ((packed_data >> MMAMorphState.packed_size) & 1) == 1
        self.spin = ((packed_data >> MMAMorphState.packed_size + 1) & 1) == 1

    def pack(self) -> int:
        morphs = self.morphs.pack()
        return morphs | (self.glove << MMAMorphState.packed_size) | (self.spin << MMAMorphState.packed_size + 1)

    async def write_flags(self, ctx: "BizHawkClientContext") -> None:
        # TODO: make list instead
        if not self.spin and not self.glove:
            # Both of these need to be frozen.
            # The glove's value doesn't really matter.
            await bizhawk.write(
                ctx.bizhawk_ctx,
                [
                    (self.address_table.power_glove, [0], "MainRAM"),
                    (self.address_table.spin_attack, [0], "MainRAM"),
                    (self.address_table.morphs, self.morphs.get_bytes(), "MainRAM"),
                ],
            )
        elif not self.spin:
            await bizhawk.write(
                ctx.bizhawk_ctx,
                [
                    (self.address_table.spin_attack, [0], "MainRAM"),
                    (self.address_table.morphs, self.morphs.get_bytes(), "MainRAM"),
                ],
            )
        elif not self.glove:
            await bizhawk.write(
                ctx.bizhawk_ctx,
                [
                    (self.address_table.power_glove, [0], "MainRAM"),
                    (self.address_table.morphs, self.morphs.get_bytes(), "MainRAM"),
                ],
            )
            # Spin only needs to be written to if it's zero
            _ = await bizhawk.guarded_write(
                ctx.bizhawk_ctx,
                [(self.address_table.spin_attack, [1], "MainRAM")],
                [(self.address_table.spin_attack, [0], "MainRAM")],
            )
        else:
            await bizhawk.write(ctx.bizhawk_ctx, [(self.address_table.morphs, self.morphs.get_bytes(), "MainRAM")])

    async def change_current_health(self, increase: bool, ctx: "BizHawkClientContext"):
        # Grab the current health and the max health
        data = (await bizhawk.read(ctx.bizhawk_ctx, [(self.address_table.current_health, 2, "MainRAM")]))[0]
        current_health = data[0]
        max_health = data[1]

        if increase:
            new_health = current_health + 1 if current_health < max_health else max_health
        else:
            new_health = current_health - 1 if current_health > 0 else 0
        await bizhawk.write(ctx.bizhawk_ctx, [(self.address_table.current_health, [new_health], "MainRAM")])

    async def change_max_health(self, increase: bool, ctx: "BizHawkClientContext"):
        # Grab the max health
        data = (await bizhawk.read(ctx.bizhawk_ctx, [(self.address_table.current_health, 2, "MainRAM")]))[0]
        current_health = data[0]
        max_health = data[1]

        if increase:
            new_max_health = max_health + 1 if max_health < self.max_limit else self.max_limit
        else:
            new_max_health = max_health - 1 if max_health > 0 else 0

        await bizhawk.write(ctx.bizhawk_ctx, [(self.address_table.max_health, [new_max_health], "MainRAM")])

        # Ensure the current health cannot be above the max health
        if current_health > new_max_health:
            await bizhawk.write(ctx.bizhawk_ctx, [(self.address_table.current_health, [new_max_health], "MainRAM")])

    async def change_current_lives(self, increase: bool, ctx: "BizHawkClientContext"):
        # Grab the current health and the max health
        data = (await bizhawk.read(ctx.bizhawk_ctx, [(self.address_table.current_lives, 1, "MainRAM")]))[0]
        current_lives = data[0]

        if increase:
            new_lives = current_lives + 1 if current_lives < self.max_limit else self.max_limit
        else:
            new_lives = current_lives - 1 if current_lives > 0 else 0
        await bizhawk.write(ctx.bizhawk_ctx, [(self.address_table.current_lives, [new_lives], "MainRAM")])


class MMAGameState(MMAAddressTableConsumer):
    saved_custom_marker_size: int = 1
    saved_received_index_size: int = 2
    saved_abilities_and_goal_size: int = 2
    saved_level_unlocks_size: int = ceil(len(region_lookup) / 8.0)

    custom_marker_value: int = 67

    def __init__(
        self,
        address_table: AddressTable,
        boss_goal_count: int,
        energy_thresholds: list[float],
    ) -> None:
        super().__init__(address_table)
        self.boss_goal_count: int = boss_goal_count

        self.player: MMAPlayerState = MMAPlayerState(address_table)
        self.bosses_beaten: list[bool] = [False] * 5
        self.level_states: dict[str, MMALevelState] = {
            region.game_identifier: MMALevelState(
                self.address_table,
                region,
                address_table.level_state + (i * MMALevelState.level_state_total_size),
                energy_thresholds,
            )
            for i, region in enumerate(non_boss_region_lookup.values())
        }
        self.level_unlocks: list[bool] = [False for _ in region_lookup.values()]
        self.amulets: dict[LocationType, MMAAmuletState] = {
            LocationType.NOSEFERATU_AMULET: MMAAmuletState(0),
            LocationType.WEREBEAR_AMULET: MMAAmuletState(4),
            LocationType.KER_MONSTER_AMULET: MMAAmuletState(8),
            LocationType.MUCK_MONSTER_AMULET: MMAAmuletState(12),
            LocationType.GHOUL_FRIEND_AMULET: MMAAmuletState(16),
        }

        self.active_level_name: str = ""
        self.last_amulets_flags: list[bytes] = [bytes(0)]
        self.goaled: bool = False
        self.last_received_index: int = 0

    # For writing persistent flags that need to be set every frame.
    # If this function returns False, we should not update this frame.
    async def try_write_flags(self, ctx: "BizHawkClientContext") -> bool:
        # This flag seems to be 16 when a level is ready, and 64 when a level is loading.
        load_state = await bizhawk.read(ctx.bizhawk_ctx, [(self.address_table.loading_state, 1, "MainRAM")])
        load_state_int = int.from_bytes(load_state[0], byteorder="little")
        if load_state_int != 16:
            return False

        if self.active_level_name == "HUB":
            # Write level unlocks, always have all zones unlocked
            write_list: list[int] = [0xFF if unlocked else 0x00 for unlocked in self.level_unlocks]
            await bizhawk.write(
                ctx.bizhawk_ctx,
                [
                    (self.address_table.level_unlock_states, write_list, "MainRAM"),
                    (self.address_table.zone_unlocked_count, [5], "MainRAM"),
                ],
            )
        else:
            await self.player.write_flags(ctx)
        return True

    async def receive_items(self, ctx: "BizHawkClientContext") -> None:
        new_items = ctx.items_received[self.last_received_index :]
        if len(new_items) == 0:
            return

        for net_item in new_items:
            item = item_id_to_item[net_item.item]
            match item:
                case MMAAbilityItemData():
                    match item.ability_type:
                        case AbilityFlag.GLIDE:
                            self.player.morphs.glide = True
                        case AbilityFlag.CLIMB:
                            self.player.morphs.climb = True
                        case AbilityFlag.PUSH:
                            self.player.morphs.push = True
                        case AbilityFlag.SWIM:
                            self.player.morphs.swim = True
                        case AbilityFlag.SMASH:
                            self.player.morphs.smash = True
                        case AbilityFlag.SPIN:
                            self.player.spin = True
                        case AbilityFlag.GLOVE:
                            self.player.glove = True
                        case _:
                            pass
                case MMALevelItemData():
                    self.level_unlocks[item.index] = True
                    pass
                case MMAFillerItemData():
                    match item.item_type:
                        case FillerType.GAIN_HEALTH:
                            await self.player.change_current_health(True, ctx)
                            pass
                        case FillerType.GAIN_HEART:
                            await self.player.change_max_health(True, ctx)
                            pass
                        case FillerType.GAIN_LIFE:
                            await self.player.change_current_lives(True, ctx)
                            pass
                        case _:
                            pass
                case MMATrapItemData():
                    match item.trap_type:
                        case TrapType.LOSE_HEALTH:
                            await self.player.change_current_health(False, ctx)
                            pass
                        case TrapType.LOSE_HEART:
                            await self.player.change_max_health(False, ctx)
                            pass
                        case TrapType.LOSE_LIFE:
                            await self.player.change_current_lives(False, ctx)
                            pass
                        case _:
                            pass
                    pass
                case _:
                    pass

        self.last_received_index = len(ctx.items_received)

    async def get_checked_locations(self, ctx: "BizHawkClientContext") -> None:
        from CommonClient import logger

        # TODO: move amulets into separate class
        amulets_flag = await bizhawk.read(ctx.bizhawk_ctx, [(self.address_table.amulets, 3, "MainRAM")])
        if amulets_flag != self.last_amulets_flags:
            self.last_amulets_flags = amulets_flag
            flags_int = int.from_bytes(amulets_flag[0], byteorder="little")

            # Extract amulet pickup changes
            amulet_collections: list[int] = []
            for amulet_type, state in self.amulets.items():
                changes = state.get_checked_locations(flags_int)
                # TODO: emit location collection
                if len(changes) > 0:
                    logger.info(f"'{amulet_type}' changes - {changes}")
                    for item in changes:
                        location = location_type_lookup[amulet_type][item]
                        ap_id = location_name_to_id[location.full_identifier]
                        amulet_collections.append(ap_id)

            if len(amulet_collections) > 0:
                # TODO: do we want to do anything with this information?
                _ = await ctx.check_locations(amulet_collections)

        if (level := self.level_states.get(self.active_level_name)) is not None:
            level_changes = await level.get_checked_locations(ctx)
            if len(level_changes) > 0:
                _ = await ctx.check_locations(level_changes)
            pass
        else:
            # TODO: Find a better method of checking this
            bosses_beaten_bytes = await bizhawk.read(
                ctx.bizhawk_ctx, [(self.address_table.bosses_beaten, 1, "MainRAM")]
            )
            bosses_beaten = int.from_bytes(bosses_beaten_bytes[0], byteorder="little")
            if bosses_beaten > 0:
                await bizhawk.write(ctx.bizhawk_ctx, [(self.address_table.bosses_beaten, [0], "MainRAM")])
                # This flag stores the highest value boss number. For our purposes we treat this as
                # the most recent boss number.
                boss_index = bosses_beaten - 1
                self.bosses_beaten[boss_index] = True
                location = location_type_lookup[LocationType.BOSS][boss_index]
                ap_id = location_name_to_id[location.full_identifier]
                _ = await ctx.check_locations([ap_id])

                completed_bosses = list(filter(lambda b: b, self.bosses_beaten))
                if len(completed_bosses) >= self.boss_goal_count and not self.goaled:
                    logger.info("Goaled")
                    self.goaled = True
                    await ctx.send_msgs(
                        [
                            {
                                "cmd": "StatusUpdate",
                                "status": ClientStatus.CLIENT_GOAL,
                            }
                        ]
                    )
            pass
        return

    async def initialize(self, ctx: "BizHawkClientContext") -> None:
        """Sets up the initial state from the current game state.
        Loads the current state from save data and sends out any checked locations."""
        await self.get_checked_locations(ctx)
        level_changes: list[int] = []
        for name, level in self.level_states.items():
            level_changes.extend(
                await level.initialize(
                    ctx,
                    self.active_level_name == name,
                )
            )
        if len(level_changes) > 0:
            _ = await ctx.check_locations(level_changes)

        sizes: list[int] = [
            self.saved_custom_marker_size,
            self.saved_received_index_size,
            self.saved_abilities_and_goal_size,
            self.saved_level_unlocks_size,
        ]
        lookups: list[tuple[int, int, str]] = []
        total_size: int = 0
        for size in sizes:
            lookups.append((self.address_table.custom_save_data + total_size, size, "MainRAM"))
            total_size += size
        custom_data = await bizhawk.read(ctx.bizhawk_ctx, lookups)

        def get_int(index: int) -> int:
            return int.from_bytes(custom_data[index], byteorder="little")

        custom_marker = get_int(0)
        if custom_marker != self.custom_marker_value:
            # Not archipelago save (yet). Initial save information may be incorrect.
            return
        self.last_received_index = get_int(1)
        player_data = get_int(2)
        self.player.unpack(player_data)
        self.goaled = ((player_data >> MMAPlayerState.packed_size) & 1) == 1

        unlocks_int = get_int(2)
        self.level_unlocks = [((unlocks_int >> idx) & 1) == 1 for idx, _ in enumerate(self.level_unlocks)]

    async def save(self, ctx: "BizHawkClientContext") -> None:
        # TODO: does this need to wait for a save to become active?
        # if so, maybe this should store in both MainRAM and also Memcard?
        level_unlocks: int = 0
        for idx, unlocked in enumerate(self.level_unlocks):
            level_unlocks |= unlocked << idx

        values: dict[int, int] = {
            self.saved_custom_marker_size: self.custom_marker_value,
            self.saved_received_index_size: self.last_received_index,
            self.saved_abilities_and_goal_size: self.player.pack() | (self.goaled << MMAPlayerState.packed_size),
            self.saved_level_unlocks_size: level_unlocks,
        }
        lookups: list[tuple[int, Sequence[int], str]] = []
        total_size: int = 0
        for size, value in values.items():
            lookups.append(
                (
                    self.address_table.custom_save_data + total_size,
                    value.to_bytes(size, "little"),
                    "MainRAM",
                )
            )
            total_size += size
        await bizhawk.write(ctx.bizhawk_ctx, lookups)


class MMAClient(BizHawkClient):
    game = game_name
    system = "PSX"
    items_handling = 0b111
    patch_suffix = None

    # Memory sizes
    game_identifier_size: int = 11
    level_name_size: int = 10

    version_addresses: ClassVar[dict[str, AddressTable]] = {
        "SLUS_012.38": ntsc_addresses,
        # "SCES_024.03": pal_addresses,
    }

    def __init__(self):
        super().__init__()

        self.state: MMAGameState
        self.last_received_index: int = 0
        self.goaled: bool = False
        self.was_save_loaded: bool = False
        self.address_table: AddressTable

    def reset_state(self, level_name: str | None = None) -> None:
        # TODO: options
        self.state = MMAGameState(self.address_table, 1, [0.5, 1.0])
        if level_name is not None:
            self.state.active_level_name = level_name

    async def validate_rom(self, ctx: "BizHawkClientContext") -> bool:
        try:
            found_table: AddressTable | None = None
            for name, table in self.version_addresses.items():
                rom_name = (
                    (
                        await bizhawk.read(
                            ctx.bizhawk_ctx, [(table.game_identifier, self.game_identifier_size, "MainRAM")]
                        )
                    )[0]
                ).decode("ascii")
                if rom_name == name:
                    found_table = table
                    break
            if found_table is None:
                return False
        except bizhawk.RequestFailedError:
            return False

        self.address_table = found_table
        ctx.game = self.game
        ctx.items_handling = self.items_handling
        ctx.want_slot_data = True
        ctx.watcher_timeout = 0.125
        return True

    def on_package(self, ctx: "BizHawkClientContext", cmd: str, args: dict[object, object]) -> None:
        super().on_package(ctx, cmd, args)  # pyright: ignore[reportUnknownMemberType]

        match cmd:
            case "Connected":
                # TODO: Read relevant slot data & reset state
                pass
            case _:
                pass
            # TODO: race countdown
        pass

    async def set_auth(self, ctx: "BizHawkClientContext") -> None:
        await ctx.get_username()

    async def game_watcher(self, ctx: "BizHawkClientContext") -> None:
        from CommonClient import logger

        # TODO: we probably want to keep state as `None` until the player is connected, and reset when disconnected.
        if ctx.server is None or ctx.server.socket.closed or ctx.slot_data is None or ctx.auth is None:
            # Just reset state whenever we disconnect.
            self.reset_state()
            return

        level_name = await self.get_level_name(ctx)
        if level_name != self.state.active_level_name:
            # TODO: emit events for trackers and stuff
            self.state.active_level_name = level_name
            logger.info(f"Level changed to '{self.state.active_level_name}'")

        # TODO: probably others
        if (
            self.state.active_level_name == ""
            or self.state.active_level_name == "FRONT1"
            or self.state.active_level_name == "GLOBAL"
            or self.state.active_level_name.startswith("DEMO")
        ):
            # Not in-game.
            if self.was_save_loaded:
                # Player returned to menu. Reset state.
                # Copy the old level name to prevent re-firing any listeners on the level change.
                self.reset_state(self.state.active_level_name)
            self.was_save_loaded = False
            return

        if not self.was_save_loaded:
            # TODO: read last received index from save data
            await self.state.initialize(ctx)
        self.was_save_loaded = True

        if not await self.state.try_write_flags(ctx):
            # Game is loaded correctly, but is not in a state to write anything.
            return

        # Locations may have triggered own items, so check those first.
        await self.state.get_checked_locations(ctx)
        await self.state.receive_items(ctx)
        # Persist the state in save memory
        await self.state.save(ctx)
        return

    async def get_level_name(self, ctx: "BizHawkClientContext") -> str:
        level_bytes = (
            await bizhawk.read(
                ctx.bizhawk_ctx, [(self.address_table.active_level_name, self.level_name_size, "MainRAM")]
            )
        )[0]
        level_str = ""
        for b in level_bytes:
            # End of name string is denoted by null char.
            if b == 0:
                break
            level_str += chr(b)
        return level_str
