from typing import TYPE_CHECKING, ClassVar, NamedTuple

from worlds.muppet_monster_adventure.addresses import AddressTable, game_version_addresses

if TYPE_CHECKING:
    from worlds._bizhawk.context import BizHawkClientContext

import worlds._bizhawk as bizhawk
from NetUtils import ClientStatus
from worlds._bizhawk.client import BizHawkClient

from .items import MMAAbilityItemData, MMAFillerItemData, MMALevelItemData, MMATrapItemData, item_id_to_item
from .locations import (
    LocationType,
    location_name_to_id,
    location_type_lookup,
    location_type_lookup_by_region,
    non_boss_region_lookup,
    region_lookup,
)
from .shared import AbilityFlag, FillerType, TrapType, game_name


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

    def process_changes(self, data: int) -> list[int]:
        new_flags = self.split_flags(data)
        changes: list[int] = []
        for i in range(self.size):
            if new_flags[i] and new_flags[i] != self.flags[i]:
                changes.append(i)
                self.flags[i] = True
        return changes


class MMAMorphState:
    def __init__(self) -> None:
        self.glide: bool = False
        self.climb: bool = False
        self.push: bool = False
        self.swim: bool = False
        self.smash: bool = False

    def get_bytes(self) -> bytes:
        packed_data = (self.glide << 0) | (self.climb << 1) | (self.push << 2) | (self.swim << 3) | (self.smash << 4)
        return packed_data.to_bytes(2, "little")


class LevelUpdate(NamedTuple):
    previous_energy: int
    previous_tokens: int
    energy: int | None
    tokens: int | None
    bonus_changes: list[int] | None


class MMALevelState:
    level_state_size: int = 6

    def __init__(
        self,
        name: str,
        address: int,
        max_energy: int,
    ) -> None:
        self.name: str = name
        self.address: int = address
        self.max_energy: int = max_energy
        self.bonus: MMAFlagField = MMAFlagField(size=5, offset=0)
        # self.coins: int = 0
        self.tokens: int = 0
        self.energy: int = 0

    # TODO: this should just return the location ids which were collected
    async def process_changes(self, ctx: "BizHawkClientContext") -> LevelUpdate:
        # TODO: technically we could do visit-sanity if we wanted, since the game tracks it.
        # Would need to adjust all of this though, since it's 2 bytes prior to the Bonus.
        data = (await bizhawk.read(ctx.bizhawk_ctx, [(self.address, self.level_state_size, "MainRAM")]))[0]

        bonus_changes = self.bonus.process_changes(data[0])
        updated_tokens = data[1]
        # coins = int.from_bytes(data[2:4], byteorder="little")
        updated_energy = int.from_bytes(data[4:6], byteorder="little")

        update = LevelUpdate(
            self.energy,
            self.tokens,
            updated_energy if updated_energy > self.energy else None,
            updated_tokens if updated_tokens > self.tokens else None,
            bonus_changes if len(bonus_changes) > 0 else None,
        )

        # Sometimes fields like these are flipped up and down for effect.
        # Don't know if these specifically are, but better safe than sorry.
        self.energy = max(updated_energy, self.energy)
        # self.coins = max(coins, self.coins)
        self.tokens = max(updated_tokens, self.tokens)
        return update

    def print(self) -> str:
        return f"Tokens: {self.tokens}, Energy: {self.energy}, Bonus: {self.bonus.flags}"


class MMAAmuletState:
    # TODO: maybe provide item identifier list
    def __init__(self, offset: int) -> None:
        self.flags: MMAFlagField = MMAFlagField(4, offset)

    # TODO: this should return location ids
    def process_changes(self, data: int) -> list[int]:
        return self.flags.process_changes(data)


class MMAPlayerState(MMAAddressTableConsumer):
    def __init__(self, address_table: AddressTable) -> None:
        super().__init__(address_table)
        self.morphs: MMAMorphState = MMAMorphState()
        # Limit the maximum health and lives to this number
        self.max_limit: int = 100

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
    def __init__(self, address_table: AddressTable, boss_goal_count: int) -> None:
        super().__init__(address_table)
        self.boss_goal_count: int = boss_goal_count

        self.player: MMAPlayerState = MMAPlayerState(address_table)
        self.bosses_beaten: list[bool] = [False] * 5
        self.level_states: dict[str, MMALevelState] = {
            region.identifier: MMALevelState(
                region.name,
                address_table.level_state_start + (i * MMALevelState.level_state_size),
                region.energy_count,
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
                    (self.address_table.level_unlock, write_list, "MainRAM"),
                    (self.address_table.zones_unlock, [5], "MainRAM"),
                ],
            )
        else:
            # Write morph powers
            await bizhawk.write(
                ctx.bizhawk_ctx, [(self.address_table.morphs, self.player.morphs.get_bytes(), "MainRAM")]
            )
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
                        case _:
                            # TODO: glove & spin
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

    async def check_locations(self, ctx: "BizHawkClientContext") -> None:
        from CommonClient import logger

        # TODO: move amulets into separate class
        amulets_flag = await bizhawk.read(ctx.bizhawk_ctx, [(self.address_table.amulets, 3, "MainRAM")])
        if amulets_flag != self.last_amulets_flags:
            self.last_amulets_flags = amulets_flag
            flags_int = int.from_bytes(amulets_flag[0], byteorder="little")

            # Extract amulet pickup changes
            amulet_collections: list[int] = []
            for amulet_type, state in self.amulets.items():
                changes = state.process_changes(flags_int)
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
            level_state_collections: list[int] = []
            region_lookup = location_type_lookup_by_region[level.name]

            level_changes = await level.process_changes(ctx)
            # Energy changes
            if level_changes.energy is not None:
                half_energy = level.max_energy / 2
                if level.energy >= half_energy and level_changes.previous_energy < half_energy:
                    # Emit 50% energy
                    location = region_lookup[LocationType.ENERGY][0]
                    ap_id = location_name_to_id[location.full_identifier]
                    level_state_collections.append(ap_id)
                    pass
                elif level.energy == level.max_energy and level_changes.previous_energy < level.max_energy:
                    # Emit 100% energy
                    location = region_lookup[LocationType.ENERGY][1]
                    ap_id = location_name_to_id[location.full_identifier]
                    level_state_collections.append(ap_id)
                    pass
            # Token changes
            if level_changes.tokens is not None:
                for i in range(level_changes.tokens - level_changes.previous_tokens):
                    location = region_lookup[LocationType.TOKEN][level_changes.previous_tokens + i]
                    ap_id = location_name_to_id[location.full_identifier]
                    level_state_collections.append(ap_id)
                pass

            # Bonus changes
            if level_changes.bonus_changes is not None:
                for idx in level_changes.bonus_changes:
                    location = region_lookup[LocationType.BONUS][idx]
                    ap_id = location_name_to_id[location.full_identifier]
                    level_state_collections.append(ap_id)
                pass

            if len(level_state_collections) > 0:
                _ = await ctx.check_locations(level_state_collections)
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


class MMAClient(BizHawkClient):
    game = game_name
    system = "PSX"
    items_handling = 0b111
    patch_suffix = None

    # Memory sizes
    game_identifier_size: int = 11
    level_name_size: int = 10

    def __init__(self):
        super().__init__()

        self.state: MMAGameState
        self.last_received_index: int = 0
        self.goaled: bool = False
        self.was_save_loaded: bool = False
        self.active_level_name: str = ""
        self.address_table: AddressTable

    def init_state(self, level_name: str | None = None) -> None:
        # TODO: goal options?
        self.state = MMAGameState(self.address_table, 1)
        if level_name is not None:
            self.state.active_level_name = level_name

    async def validate_rom(self, ctx: "BizHawkClientContext") -> bool:
        try:
            found_table: AddressTable | None = None
            for name, table in game_version_addresses.items():
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
            self.init_state()
            return

        level_name = await self.get_level_name(ctx)
        if level_name != self.state.active_level_name:
            # TODO: emit events for trackers and stuff
            self.state.active_level_name = level_name
            logger.info(f"Level changed to '{self.active_level_name}'")

        # TODO: probably others
        if (
            self.active_level_name == ""
            or self.active_level_name == "FRONT1"
            or self.active_level_name == "GLOBAL"
            or self.active_level_name.startswith("DEMO")
        ):
            # Not in-game.
            if self.was_save_loaded:
                # Player returned to menu. Reset state.
                # Copy the old level name to prevent re-firing any listeners on the level change.
                self.init_state(self.state.active_level_name)
            self.was_save_loaded = False
            return
        self.was_save_loaded = True

        # TODO: HERE is where we should init state, once a save is loaded.
        # We should store metadata in the save if possible so we can validate it first
        # and avoid re-receiving filler items.

        if not await self.state.try_write_flags(ctx):
            # Game is loaded correctly, but is not in a state to write anything.
            return

        # Locations may have triggered own items, so check those first.
        await self.state.check_locations(ctx)
        await self.state.receive_items(ctx)
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
