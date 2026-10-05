from typing import cast

from BaseClasses import Item, Location, MultiWorld, Region
from rule_builder import rules
from worlds.AutoWorld import World

from .client import *  # noqa: F403
from .items import (
    MMAAbilityItemData,
    MMALevelItemData,
    ability_to_item,
    filler_items_table,
    item_name_groups,
    item_name_to_id,
    required_items_table,
    trap_items_table,
)
from .locations import (
    LocationType,
    MMABossLocationData,
    all_locations_table,
    location_name_groups,
    location_name_to_id,
    location_type_lookup,
)
from .shared import AbilityFlag, LevelName, game_name, whitelisted_starting_levels


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

    origin_region_name = LevelName.HUB.value

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
        for item in self.get_pre_fill_items():
            self.push_precollected(item)
        return

    def create_regions(self) -> None:
        super().create_regions()

        # Hub always required as it's the starting level.
        hub_region = Region(LevelName.HUB.value, self.player, self.multiworld)
        self.multiworld.regions.append(hub_region)

        regions: list[Region] = []
        for region_def in all_locations_table:
            region = Region(region_def.name, self.player, self.multiworld)
            locations: dict[str, int] = {}
            for loc in region_def.locations:
                self.location_count += 1
                locations.update({loc.full_identifier: location_name_to_id[loc.full_identifier]})
            region.add_locations(locations)
            regions.append(region)
        self.multiworld.regions.extend(regions)
        return

    def create_items(self) -> None:
        super().create_items()

        pool: list[Item] = []
        starter_level_name = self.random.choice(whitelisted_starting_levels)
        for item_def in required_items_table:
            item = MMAItem(item_def.name, item_def.classification, item_name_to_id[item_def.name], self.player)
            if type(item_def) is not MMALevelItemData:
                if type(item_def) is MMAAbilityItemData and (
                    item_def.ability_type == AbilityFlag.GLOVE or item_def.ability_type == AbilityFlag.SPIN
                ):
                    # TODO: Make this an option (and guide everyone to keep it on until we can reliably lock these).
                    self.starter_items.append(item)
                else:
                    pool.append(item)
            elif item_def.name != starter_level_name:
                pool.append(item)
                print(f"Adding level item: {item_def.name}")
            else:
                self.starting_level = item

        # TODO: make the weights of these options
        # Add buffer filler items to pool
        diff = self.location_count - len(pool)
        print(f"locations: {self.location_count}, items: {len(pool)}, diff: {diff}")

        trap_count = round(diff / 10)
        if diff > 0:
            for _ in range(diff - trap_count):
                item_def = self.random.choice(filler_items_table)
                pool.append(
                    MMAItem(
                        item_def.name,
                        item_def.classification,
                        item_name_to_id[item_def.name],
                        self.player,
                    )
                )
            for _ in range(trap_count):
                item_def = self.random.choice(trap_items_table)
                pool.append(
                    MMAItem(
                        item_def.name,
                        item_def.classification,
                        item_name_to_id[item_def.name],
                        self.player,
                    )
                )

        self.multiworld.itempool += pool
        return

    def set_rules(self) -> None:
        super().set_rules()

        hub_region = self.get_region(LevelName.HUB.value)
        for region_def in all_locations_table:
            region = self.get_region(region_def.name)
            # Hub can access all regions (when they are unlocked).
            # All regions can access the Hub, always.
            _ = hub_region.connect(region, None, rules.Has(region_def.name))
            _ = region.connect(hub_region, None, None)

            base_region_rule = rules.CanReachRegion(region_def.name)
            for location in region_def.locations:
                rule: rules.Rule = base_region_rule
                if location.ability_requirements is not None:
                    options: list[rules.Rule] = []
                    for option in location.ability_requirements:
                        items: list[str] = [ability_to_item[opt].name for opt in option]
                        options.append(rules.HasAll(*items))
                    rule = rules.And(rule, rules.Or(*options))
                self.set_rule(self.get_location(location.full_identifier), rule)
                if type(location) is MMABossLocationData:
                    # Same rule as the item location
                    _ = region.add_event(location.get_event_name(), rule=rule)

        boss_locations = [
            (cast(MMABossLocationData, loc)).get_event_name() for loc in location_type_lookup[LocationType.BOSS]
        ]
        self.set_completion_rule(rules.HasAll(*boss_locations))
        return
