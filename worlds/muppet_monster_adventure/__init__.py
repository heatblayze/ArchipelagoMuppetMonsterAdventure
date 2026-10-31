from typing import cast

from BaseClasses import Item, ItemClassification, Location, MultiWorld, Region
from Options import Toggle
from rule_builder import rules
from worlds.AutoWorld import World

from .client import *  # noqa: F403
from .items import (
    MMAAbilityItemData,
    MMAFillerItemData,
    MMALevelItemData,
    MMATrapItemData,
    ability_to_item,
    filler_items_table,
    item_id_to_item,
    item_name_groups,
    item_name_to_id,
    required_items_table,
    trap_items_table,
)
from .locations import (
    LocationType,
    MMABonusLetterLocationData,
    MMABossLocationData,
    MMAEnergyLocationData,
    MMALocationData,
    MMAMuppetTokenLocationData,
    MMAMuppetMinigameTokenLocationData,
    all_locations_table,
    location_name_groups,
    location_name_to_id,
    location_type_lookup,
)
from .options import MMAOptions
from .shared import HUB_LEVEL, AbilityFlag, game_name, whitelisted_starting_levels


class MMAItem(Item):
    game: str = game_name


class MMALocation(Location):
    game: str = game_name


class MuppetMonsterAdventureWorld(World):
    game = game_name

    topology_present = False  # Levels can be played in any order.

    item_name_to_id = item_name_to_id
    item_name_groups = item_name_groups
    location_name_to_id = location_name_to_id
    location_name_groups = location_name_groups

    options_dataclass = MMAOptions
    options: MMAOptions  # pyright: ignore[reportIncompatibleVariableOverride]
    origin_region_name = HUB_LEVEL

    def __init__(self, multiworld: MultiWorld, player: int):
        super().__init__(multiworld, player)
        self.starting_level: Item
        self.starter_items: list[Item] = []
        self.location_count: int = 0

    def get_filler_item_name(self) -> str:
        return self.random.choice(filler_items_table).name

    def get_pre_fill_items(self) -> list["Item"]:
        return [self.starting_level, *self.starter_items]

    def pre_fill(self) -> None:
        super().pre_fill()
        for item in [self.starting_level, *self.starter_items]:
            self.push_precollected(item)
        return

    def create_regions(self) -> None:
        super().create_regions()

        # Hub always required as it's the starting level.
        hub_region = Region(HUB_LEVEL, self.player, self.multiworld)
        self.multiworld.regions.append(hub_region)

        regions: list[Region] = []
        for region_def in all_locations_table:
            region = Region(region_def.name, self.player, self.multiworld)
            locations: dict[str, int] = {}
            for loc in region_def.locations:
                if not self.is_location_included(loc):
                    continue
                self.location_count += 1
                locations.update({loc.full_identifier: location_name_to_id[loc.full_identifier]})
            region.add_locations(locations, MMALocation)
            regions.append(region)
        self.multiworld.regions.extend(regions)
        return

    def is_location_included(self, loc: MMALocationData) -> bool:
        match loc:
            case MMABonusLetterLocationData():
                return self.options.bonus_sanity.value == Toggle.option_true
            case MMAMuppetMinigameTokenLocationData():
                return self.options.disable_minigames.value == Toggle.option_false
            case MMAMuppetTokenLocationData():
                return self.options.token_sanity.value == Toggle.option_true
            case MMAEnergyLocationData():
                return loc.energy_amount.value in self.options.energy_thresholds.value
            case _:
                return True

    def create_item(self, name: str) -> "MMAItem":
        item_id: int = self.item_name_to_id[name]
        item = item_id_to_item[item_id]

        return MMAItem(item.name, item.classification, item_id, self.player)

    def create_event(self, event: str):
        return MMAItem(event, ItemClassification.progression, None, self.player)

    def fill_slot_data(self) -> dict[str, object]:
        slot_data: dict[str, object] = {
            "start_location": self.starting_level.name,
            # "death_link": self.options.death_link.value
            "goal_count": self.options.goal.value,
            "disable_pepe_messages": self.options.disable_pepe_messages.value,
            "reword_minigame_messages": self.options.reword_minigame_messages.value,
        }
        return slot_data

    def create_items(self) -> None:
        super().create_items()

        pool: list[Item] = []
        starter_level_name = self.random.choice(whitelisted_starting_levels)
        for item_def in required_items_table:
            item = MMAItem(item_def.name, item_def.classification, item_name_to_id[item_def.name], self.player)
            match item_def:
                case MMALevelItemData():
                    if item_def.name != starter_level_name:
                        pool.append(item)
                    else:
                        self.starting_level = item
                case MMAAbilityItemData():
                    if item_def.ability_type == AbilityFlag.GLOVE or item_def.ability_type == AbilityFlag.SPIN:
                        # TODO: Make this an option (and guide everyone to keep it on until we can reliably lock these).
                        self.starter_items.append(item)
                    else:
                        pool.append(item)
                case _:
                    pool.append(item)

        # Add buffer filler items to pool
        diff = self.location_count - len(pool)

        filler_options: list[MMAFillerItemData] = [
            filler for filler in filler_items_table if self.options.filler_weights.value[filler.name] > 0
        ]
        trap_options: list[MMATrapItemData] = [
            trap for trap in trap_items_table if self.options.trap_weights.value[trap.name] > 0
        ]

        filler_weights: list[int] = [it for it in self.options.filler_weights.value.values() if it > 0]
        trap_weights: list[int] = [it for it in self.options.trap_weights.value.values() if it > 0]

        if len(filler_options) == 0 and len(trap_options) == 0:
            # Need at least one item to fill with
            filler_options = [filler_items_table[0]]
            trap_weights[0] = 1

        if len(trap_options) == 0:
            self.options.trap_ratio.value = 0
        if len(filler_options) == 0:
            self.options.trap_ratio.value = 100

        trap_count: int = 0
        if self.options.trap_ratio.value > 0:
            trap_count = round(diff / (100 / float(self.options.trap_ratio.value)))

        if diff > 0:
            filler_count: int = diff - trap_count
            if filler_count > 0:
                choices = self.random.choices(filler_options, filler_weights, k=filler_count)
                pool.extend(
                    [
                        MMAItem(
                            item_def.name,
                            item_def.classification,
                            item_name_to_id[item_def.name],
                            self.player,
                        )
                        for item_def in choices
                    ]
                )
            if trap_count > 0:
                choices = self.random.choices(trap_options, trap_weights, k=trap_count)
                pool.extend(
                    [
                        MMAItem(
                            item_def.name,
                            item_def.classification,
                            item_name_to_id[item_def.name],
                            self.player,
                        )
                        for item_def in choices
                    ]
                )

        self.multiworld.itempool += pool

        for region_def in all_locations_table:
            region = self.get_region(region_def.name)
            for location in region_def.locations:
                if type(location) is MMABossLocationData:
                    # Rule is specified later in set_rules
                    _ = region.add_event(location.get_event_name(), item_type=MMAItem)
        return

    def set_rules(self) -> None:
        super().set_rules()

        hub_region = self.get_region(HUB_LEVEL)
        for region_def in all_locations_table:
            region = self.get_region(region_def.name)
            # Hub can access all regions (when they are unlocked).
            # All regions can access the Hub, always.
            _ = hub_region.connect(region, None, rules.Has(region_def.name))
            _ = region.connect(hub_region, None, None)

            base_region_rule = rules.CanReachRegion(region_def.name)
            for location in region_def.locations:
                if not self.is_location_included(location):
                    continue
                rule: rules.Rule = base_region_rule
                if location.ability_requirements is not None:
                    options: list[rules.Rule] = []
                    for option in location.ability_requirements:
                        items: list[str] = [ability_to_item[opt].name for opt in option]
                        options.append(rules.HasAll(*items))
                    rule = rules.And(rule, rules.Or(*options))
                self.set_rule(self.get_location(location.full_identifier), rule)
                if type(location) is MMABossLocationData:
                    self.set_rule(self.get_location(location.get_event_name()), rule)

        boss_event_locations = [
            (cast(MMABossLocationData, loc)).get_event_name() for loc in location_type_lookup[LocationType.BOSS]
        ]
        self.set_completion_rule(rules.HasFromListUnique(*boss_event_locations, count=self.options.goal.value))
        return
