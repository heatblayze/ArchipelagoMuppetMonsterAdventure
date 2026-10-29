from collections.abc import Sequence
from math import ceil, floor
from typing import TYPE_CHECKING, ClassVar

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
    MMABossRegion,
    MMALocationData,
    MMARegion,
    location_name_to_id,
    location_type_lookup,
    location_type_lookup_by_region,
    region_lookup,
)
from .shared import (
    AbilityFlag,
    FillerType,
    LevelConfigurationException,
    LevelName,
    MemoryConfigurationException,
    TrapType,
    game_name,
)
from .message import MessageDisplay


class MMAAddressTableConsumer:
    def __init__(self, address_table: AddressTable) -> None:
        self.address_table: AddressTable = address_table
        pass


class MMAFlagField:
    def __init__(self, size: int, *, offset: int = 0) -> None:
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

    def unpack(self, packed_data: int) -> None:
        self.flags = [False] * self.size
        for index in range(self.size):
            self.flags[index] = ((packed_data >> index) & 1) == 1

    def pack(self) -> int:
        packed_flags: int = 0
        for index, flag in enumerate(self.flags):
            packed_flags = packed_flags | (flag << index)
        return packed_flags


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
    energy_offset: int = 4
    energy_size: int = 2
    region: MMARegion

    def __init__(
        self,
        address_table: AddressTable,
        region: MMARegion,
        state_address: int,
        energy_thresholds: list[float],
        is_boss_level: bool,
    ) -> None:
        super().__init__(address_table)
        self.region: MMARegion = region
        self.state_address: int = state_address
        self.energy_thresholds: list[float] = energy_thresholds
        self.max_energy: int = self.region.energy_count
        self.location_lookup: dict[LocationType, list[MMALocationData]] = location_type_lookup_by_region[
            self.region.name
        ]
        # For our use-case, we can just ignore the boss level information (unless we find something useful)
        self.pickup_table: LevelPickupTable | None = (
            self.address_table.level_pickup_data[LevelName(self.region.name)] if not is_boss_level else None
        )

        # State
        self.bonus: MMAFlagField = MMAFlagField(size=5, offset=0)
        self.energy: int = 0
        self.current_energy_threshold: int = -1
        self.last_pickup_addr: int = 0

        # Validation (for regular levels)
        if not is_boss_level and len(self.location_lookup[LocationType.ENERGY]) != len(self.energy_thresholds):
            raise LevelConfigurationException(
                LevelName(self.region.name),
                f"Client expects {len(self.energy_thresholds)} but the level has {len(self.location_lookup[LocationType.ENERGY])}",
            )

    # TODO: Need a method to validate all of this data on connect,
    # since the game stores all permanent pickups just after the level's general data.
    # It should include a param indicating whether this is the active level, since persisted level
    # data is only updated when the player returns to the Hub.
    async def get_checked_locations(self, ctx: "BizHawkClientContext") -> list[int]:
        if self.pickup_table is None:
            return []

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
            state_data[self.energy_offset : self.energy_offset + self.energy_size],
            byteorder="little",
            signed=False,
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
                    collected_locations.append(token_location_lookup[i].ap_id())
                    break
        return collected_locations

    async def initialize(self, ctx: "BizHawkClientContext", active: bool) -> list[int]:
        from CommonClient import logger

        if self.pickup_table is None:
            return []

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
                    collected_locations.append(token_location_lookup[i].ap_id())
                    logger.info(f"Collected token from active level {token_location_lookup[i].full_identifier}")
            else:
                if ((addresses[i][0] >> token.save_offset) & 1) == 1:
                    collected_locations.append(token_location_lookup[i].ap_id())
                    logger.info(f"Collected token from save state {token_location_lookup[i].full_identifier}")
        return collected_locations


class MMAAmuletState:
    # TODO: maybe provide item identifier list
    def __init__(self, offset: int) -> None:
        self.flags: MMAFlagField = MMAFlagField(4, offset=offset)

    # TODO: this should return location ids
    def get_checked_locations(self, data: int) -> list[int]:
        return self.flags.check(data)


class MMAPlayerState(MMAAddressTableConsumer):
    # Limit the maximum health and lives to this number
    max_limit: int = 100

    packed_size: int = MMAMorphState.packed_size + 2

    savedChickenTimer: int = 0
    """Used for saving the current timer when in a mini-game/transition"""
    pauseChickenTimer: bool = False

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
        # TODO: re-add glove and spin once we find the correct implementation
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
        await bizhawk.write(
            ctx.bizhawk_ctx,
            [(self.address_table.current_health, new_health.to_bytes(1, "little", signed=True), "MainRAM")],
        )

    async def change_max_health(self, increase: bool, ctx: "BizHawkClientContext"):
        # Grab the max health
        data = (await bizhawk.read(ctx.bizhawk_ctx, [(self.address_table.current_health, 2, "MainRAM")]))[0]
        current_health = data[0]
        max_health = data[1]

        if increase:
            new_max_health = max_health + 1 if max_health < self.max_limit else self.max_limit
        else:
            new_max_health = max_health - 1 if max_health > 0 else 0

        await bizhawk.write(
            ctx.bizhawk_ctx,
            [(self.address_table.max_health, new_max_health.to_bytes(1, "little", signed=True), "MainRAM")],
        )

        # Ensure the current health cannot be above the max health
        if current_health > new_max_health:
            await bizhawk.write(
                ctx.bizhawk_ctx,
                [(self.address_table.current_health, new_max_health.to_bytes(1, "little", signed=True), "MainRAM")],
            )

    async def full_heal(self, ctx: "BizHawkClientContext"):
        # Grab the max health
        data = (await bizhawk.read(ctx.bizhawk_ctx, [(self.address_table.max_health, 1, "MainRAM")]))[0]
        max_health = data[0]

        await bizhawk.write(
            ctx.bizhawk_ctx,
            [(self.address_table.current_health, max_health.to_bytes(1, "little", signed=True), "MainRAM")],
        )

    async def zero_health(self, ctx: "BizHawkClientContext"):
        await bizhawk.write(
            ctx.bizhawk_ctx, [(self.address_table.current_health, (0).to_bytes(1, "little", signed=True), "MainRAM")]
        )

    async def change_current_lives(self, increase: bool, ctx: "BizHawkClientContext"):
        # Grab the current lives amount
        data = (await bizhawk.read(ctx.bizhawk_ctx, [(self.address_table.current_lives, 1, "MainRAM")]))[0]
        current_lives = data[0]

        if increase:
            new_lives = current_lives + 1 if current_lives < self.max_limit else self.max_limit
        else:
            new_lives = current_lives - 1 if current_lives > 0 else 0
        await bizhawk.write(
            ctx.bizhawk_ctx,
            [(self.address_table.current_lives, new_lives.to_bytes(1, "little", signed=True), "MainRAM")],
        )

    async def change_chicken_gun_timer(self, seconds: int, ctx: "BizHawkClientContext"):
        new_seconds = seconds * self.address_table.game_timer_frames

        if self.pauseChickenTimer:
            self.savedChickenTimer = new_seconds
        else:
            await bizhawk.write(
                ctx.bizhawk_ctx,
                [(self.address_table.chicken_timer, new_seconds.to_bytes(4, "little", signed=True), "MainRAM")],
            )

    async def checkMiniGameStatus(self, ctx: "BizHawkClientContext"):
        """Returns whether or not the Player is in a Mini-Game"""
        # read the mini-game timer, if it's > 0 we're in a mini-game
        miniGameTimer = (await bizhawk.read(ctx.bizhawk_ctx, [(self.address_table.mini_game_timer, 4, "MainRAM")]))[0]
        chickenGunTimer = (await bizhawk.read(ctx.bizhawk_ctx, [(self.address_table.chicken_timer, 4, "MainRAM")]))[0]

        return int.from_bytes(chickenGunTimer, 'little', signed=True) < 0 or int.from_bytes(miniGameTimer, 'little', signed=True) > 0

    def chickenTimerIsPaused(self):
        """Returns if the chicken timer is paused"""
        return self.pauseChickenTimer

    async def suspendChickenTimer(self, ctx: "BizHawkClientContext"):
        """Pauses the chicken timer, and temporarily stores the current timer"""
        if not self.pauseChickenTimer:
            # read the current chicken timer
            data = (await bizhawk.read(ctx.bizhawk_ctx, [(self.address_table.chicken_timer, 4, "MainRAM")]))[0]
            
            self.savedChickenTimer = int.from_bytes(data, 'little', signed=True)
            # Do not override the chicken timer, if it's -1
            if self.savedChickenTimer <= 0:
                self.savedChickenTimer = 0
            else:
                await self.change_chicken_gun_timer(0, ctx)
            self.pauseChickenTimer = True

    async def restartChickenTimer(self, ctx: "BizHawkClientContext"):
        """Restarts the chicken timer at the temporarily paused value"""
        if not self.pauseChickenTimer:
            return

        await bizhawk.write(
            ctx.bizhawk_ctx,
            [(self.address_table.chicken_timer, self.savedChickenTimer.to_bytes(4, "little", signed=True), "MainRAM")],
        )
        self.pauseChickenTimer = False


class MMAGameState(MMAAddressTableConsumer):
    saved_custom_marker_size: int = 1
    saved_received_index_size: int = 2
    saved_abilities_and_goal_size: int = 2
    saved_bosses_beaten_size: int = 2
    saved_level_unlocks_size: int = ceil(len(region_lookup) / 8.0)

    custom_marker_value: int = 67
    messageDisplay: MessageDisplay

    def __init__(
        self,
        address_table: AddressTable,
        boss_goal_count: int,
        energy_thresholds: list[float],
    ) -> None:
        super().__init__(address_table)
        self.boss_goal_count: int = boss_goal_count

        self.player: MMAPlayerState = MMAPlayerState(address_table)
        self.bosses_beaten: MMAFlagField = MMAFlagField(6)
        # All levels (including bosses) have a level state and contribute the same offset.
        self.level_states: dict[str, MMALevelState] = {
            region.ingame_identifier: MMALevelState(
                self.address_table,
                region,
                address_table.level_state + (i * MMALevelState.level_state_total_size),
                energy_thresholds,
                type(region) is MMABossRegion,
            )
            for i, region in enumerate(region_lookup.values())
        }
        self.level_unlocks: MMAFlagField = MMAFlagField(len(region_lookup))
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
        self.first_check: bool = True
        self.messageDisplay = MessageDisplay(address_table)

    # For writing persistent flags that need to be set every frame.
    # If this function returns False, we should not update this frame.
    async def try_write_flags(self, ctx: "BizHawkClientContext") -> bool:
        # This flag seems to be 16 when a level is ready, and 64 when a level is loading.
        load_state = await bizhawk.read(ctx.bizhawk_ctx, [(self.address_table.loading_state, 1, "MainRAM")])
        load_state_int = int.from_bytes(load_state[0], byteorder="little")
        if load_state_int != 16:
            self.messageDisplay.levelHasChanged()
            return False

        if self.active_level_name == "HUB":
            # Write level unlocks, always have all zones unlocked
            write_list: list[int] = [0xFF if unlocked else 0x00 for unlocked in self.level_unlocks.flags]
            await bizhawk.write(
                ctx.bizhawk_ctx,
                [
                    (self.address_table.level_unlock_states, write_list, "MainRAM"),
                    # First zone is always unlocked, so this is only subsequent zones
                    (self.address_table.zone_unlocked_count, [5], "MainRAM"),
                    # Technically don't need to set this every frame, but it's fine...
                    (self.address_table.hub_autospin, (0).to_bytes(length=4, byteorder="little"), "MainRAM"),
                ],
            )
            await self.messageDisplay.updateHubMessage(ctx)
        else:
            # Disable Pepe's UI messages
            if self.active_level_name in self.level_states:
                activeLevel = self.level_states[self.active_level_name]
                if not self.messageDisplay.getMinigamesUpdated():
                    await self.messageDisplay.updateMiniGameMessages(ctx, activeLevel.region.name)

                isMiniGame = await self.player.checkMiniGameStatus(ctx)
                if isMiniGame:
                    await self.player.suspendChickenTimer(ctx)
                elif self.player.chickenTimerIsPaused():
                    await self.player.restartChickenTimer(ctx)
            else:
                await self.messageDisplay.clearPepeMessage(ctx)

            # TODO: we need to write the cheat (or an alternative) that allows you to always return to the Hub.
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
                    self.level_unlocks.flags[item.index] = True
                    pass
                case MMAFillerItemData():
                    match item.item_type:
                        case FillerType.GAIN_HEALTH:
                            await self.player.change_current_health(True, ctx)
                        case FillerType.GAIN_HEART:
                            await self.player.change_max_health(True, ctx)
                        case FillerType.GAIN_LIFE:
                            await self.player.change_current_lives(True, ctx)
                            pass
                        case FillerType.CHICKEN_TIME_15_SEC:
                            seconds = 15
                            await self.player.change_chicken_gun_timer(seconds, ctx)
                            pass
                        case FillerType.CHICKEN_TIME_30_SEC:
                            seconds = 30
                            await self.player.change_chicken_gun_timer(seconds, ctx)
                            pass
                        case FillerType.CHICKEN_TIME_1_MIN:
                            seconds = 60
                            await self.player.change_chicken_gun_timer(seconds, ctx)
                        case FillerType.FULL_HEAL:
                            await self.player.full_heal(ctx)
                case MMATrapItemData():
                    match item.trap_type:
                        case TrapType.LOSE_HEALTH:
                            await self.player.change_current_health(False, ctx)
                        case TrapType.LOSE_HEART:
                            await self.player.change_max_health(False, ctx)
                        case TrapType.LOSE_LIFE:
                            await self.player.change_current_lives(False, ctx)
                        case TrapType.CHICKEN_TIME_1_SEC:
                            seconds = 1
                            await self.player.change_chicken_gun_timer(seconds, ctx)
                        case TrapType.CHICKEN_TIME_2_SEC:
                            seconds = 2
                            await self.player.change_chicken_gun_timer(seconds, ctx)
                        case TrapType.CHICKEN_TIME_5_SEC:
                            seconds = 5
                            await self.player.change_chicken_gun_timer(seconds, ctx)
                        case TrapType.ONE_HIT_KO:
                            await self.player.zero_health(ctx)
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
            # There 100% is, because the Hub displays bosses differently when I *actually* defeat them.
            # Nope! That's a bust. The game colours it gold when you have visited the level + have this address below high enough.
            bosses_beaten_bytes = await bizhawk.read(
                ctx.bizhawk_ctx, [(self.address_table.bosses_beaten, 1, "MainRAM")]
            )
            bosses_beaten = int.from_bytes(bosses_beaten_bytes[0], byteorder="little")
            if bosses_beaten > 0:
                await bizhawk.write(ctx.bizhawk_ctx, [(self.address_table.bosses_beaten, [0], "MainRAM")])
                # This flag stores the highest value boss number. For our purposes we treat this as
                # the most recent boss number.
                boss_index = bosses_beaten - 1
                self.bosses_beaten.flags[boss_index] = True
                location = location_type_lookup[LocationType.BOSS][boss_index]
                ap_id = location_name_to_id[location.full_identifier]
                _ = await ctx.check_locations([ap_id])

                completed_bosses = list(filter(lambda b: b, self.bosses_beaten.flags))
                if len(completed_bosses) >= self.boss_goal_count and not self.goaled:
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
        from CommonClient import logger

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
            self.saved_bosses_beaten_size,
            self.saved_level_unlocks_size,
        ]
        lookups: list[tuple[int, int, str]] = []
        total_size: int = 0
        for size in sizes:
            lookups.append((self.address_table.custom_save_data + total_size, size, "MainRAM"))
            total_size += size
        custom_data = await bizhawk.read(ctx.bizhawk_ctx, lookups)

        current_index: int = -1

        def next_int() -> int:
            nonlocal current_index
            current_index += 1
            return int.from_bytes(custom_data[current_index], byteorder="little")

        custom_marker = next_int()
        if custom_marker != self.custom_marker_value:
            # Not archipelago save (yet). Initial save information may be incorrect.
            return
        self.last_received_index = next_int()
        player_data = next_int()
        self.player.unpack(player_data)
        self.goaled = ((player_data >> MMAPlayerState.packed_size) & 1) == 1

        bosses_beaten_int = next_int()
        self.bosses_beaten.unpack(bosses_beaten_int)

        level_unlocks_int = next_int()
        self.level_unlocks.unpack(level_unlocks_int)

    async def save(self, ctx: "BizHawkClientContext") -> None:
        # TODO: if we really need to (in the event that this overlaps with used data)
        # we can replace this with just the received index and skip over filler items when receiving initially.
        values: list[tuple[int, int]] = [
            (self.saved_custom_marker_size, self.custom_marker_value),
            (self.saved_received_index_size, self.last_received_index),
            (self.saved_abilities_and_goal_size, self.player.pack() | (self.goaled << MMAPlayerState.packed_size)),
            (self.saved_bosses_beaten_size, self.bosses_beaten.pack()),
            (self.saved_level_unlocks_size, self.level_unlocks.pack()),
        ]
        lookups: list[tuple[int, Sequence[int], str]] = []
        total_size: int = 0
        for size, value in values:
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
    items_handling = 0b111  # Receive all items
    patch_suffix = None

    # Memory sizes
    game_identifier_size: ClassVar[int] = 11
    level_name_size: ClassVar[int] = 10

    version_addresses: ClassVar[dict[str, AddressTable]] = {
        "SLUS_012.38": ntsc_addresses,
        # "SCES_024.03": pal_addresses,
    }

    hub_cheat_values: ClassVar[list[int]] = [
        0x0100,
        0x3484,
        0x1000,
        0x0008,
        0x1021,
        0xAC64,
        0x0100,
        0x3484,
        0x1000,
        0x0008,
        0x1021,
        0xAC64,
    ]

    energy_thresholds: ClassVar[list[float]] = [0.5, 1.0]

    def __init__(self):
        super().__init__()

        self.state: MMAGameState
        self.last_received_index: int = 0
        self.goaled: bool = False
        self.goal_target: int = 6
        self.was_save_loaded: bool = False
        self.address_table: AddressTable

    def reset_state(self, level_name: str | None = None) -> None:
        self.state = MMAGameState(self.address_table, self.goal_target, self.energy_thresholds)
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
                if ctx.slot_data is not None:
                    self.goal_target = ctx.slot_data["goal_count"] or 6
                # Ensure to reset the state in case something has changed here.
                self.reset_state()
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
            self.was_save_loaded = False
            return

        try:
            level_name = await self.get_level_name(ctx)
            if level_name != self.state.active_level_name:
                # TODO: emit events for trackers and stuff
                self.state.active_level_name = level_name

            if self.state.active_level_name == "FRONT1":
                # Force (every frame) setting the cheat locations to 0 to disable them from functioning
                await bizhawk.write(
                    ctx.bizhawk_ctx,
                    [
                        (self.address_table.cheat_menu_level_select, (0).to_bytes(1, "little"), "MainRAM"),
                        (self.address_table.cheat_permanent_level_unlock, (0).to_bytes(1, "little"), "MainRAM"),
                        (self.address_table.cheat_permanent_morph_unlock, (0).to_bytes(1, "little"), "MainRAM"),
                    ],
                )

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
                await self.state.initialize(ctx)
                self.was_save_loaded = True
                await self.write_one_time_flags(ctx)

            if not await self.state.try_write_flags(ctx):
                # Game is loaded correctly, but is not in a state to write anything.
                return

            # Locations may have triggered own items, so check those first.
            await self.state.get_checked_locations(ctx)
            await self.state.receive_items(ctx)
            # Persist the state in save memory
            await self.state.save(ctx)
        except bizhawk.RequestFailedError as ex:
            logger.error(f"Bizhawk connection failed: {ex}")
        except Exception as genericEx:
            logger.error(f"Forcibly disconnecting due to an unknown error: {genericEx}\n")
            await ctx.disconnect(False)

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

    async def write_one_time_flags(self, ctx: "BizHawkClientContext") -> None:
        item_len = len(self.address_table.always_access_hub)
        if item_len != 12:
            raise MemoryConfigurationException("always_access_hub", f"expected length of 12 but got {item_len}")
        await bizhawk.write(
            ctx.bizhawk_ctx,
            [
                (
                    self.address_table.always_access_hub[index],
                    (self.hub_cheat_values[index]).to_bytes(2, "little"),
                    "MainRAM",
                )
                for index in range(item_len)
            ],
        )
