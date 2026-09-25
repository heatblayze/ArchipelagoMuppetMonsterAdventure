from enum import Enum

from .shared import AbilityFlag, LevelName, any_weapon_flag, base_id


class LocationType(Enum):
    NOSEFERATU_AMULET = "Noseferatu Amulet"
    WEREBEAR_AMULET = "Werebear Amulet"
    KER_MONSTER_AMULET = "Ker-monster Amulet"
    MUCK_MONSTER_AMULET = "Muck Monster Amulet"
    GHOUL_FRIEND_AMULET = "Ghoul-friend Amulet"
    ENERGY = "Evil Energy"
    TOKEN = "Muppet Token"
    BONUS = "Bonus Letter"
    BOSS = "Boss Defeat"


class MMALocationData:
    ability_requirements: list[AbilityFlag] | None

    def __init__(
        self,
        name: str,
        type: LocationType,
        ability_requirements: list[AbilityFlag] | None = None,
    ):
        self.name: str = name
        self.type: LocationType = type
        # Each flag lists the unique combination of abilities which unlocks this location.
        # Alternatives should be provided as a separate entry.
        # e.g. The location can be unlocked by either "climb and swim" OR "climb and glide".
        # This would be represented as: [AbilityFlag.CLIMB | AbilityFlag.SWIM, AbilityFlag.CLIMB | AbilityFlag.GLIDE]
        self.ability_requirements = ability_requirements
        self.full_identifier: str = ""

    def ap_id(self) -> int:
        return location_name_to_id[self.full_identifier]


class MMARegion:
    def __init__(
        self,
        name: LevelName,
        identifier: str,
        energy_count: int,
        locations: list[MMALocationData],
    ) -> None:
        self.name: str = name.value
        self.identifier: str = identifier
        self.energy_count: int = energy_count
        self.locations: list[MMALocationData] = locations
        pass


class MMABossRegion(MMARegion):
    def __init__(
        self,
        name: LevelName,
        identifier: str,
        locations: list[MMALocationData],
    ) -> None:
        super().__init__(name, identifier, 0, locations)
        pass


# TODO: currently we're assuming checks can be done without caring about taking damage
# The iframes are very lenient, allowing you to get past basically every enemy,
# and the levels tend to have a good number of recovery hearts.
# BUT!! (and this is a big BUTT) the game does get notably harder to play this way after zone 1.
# Playtesting is required here...

# TODO: tokens are no longer a count, but individual locations.

# Note: The order of basically all of these matters, since the client depends on this to check world state.
all_locations_table: list[MMARegion] = [
    MMARegion(
        LevelName.PEACOCK_PURGATORY,
        "CASTLE1",
        300,
        [
            # Amulets
            MMALocationData(
                "Wocka Wocka Werebear Amulet - By tutorial flags",
                LocationType.WEREBEAR_AMULET,
            ),
            MMALocationData(
                "Wocka Wocka Werebear Amulet - By climbable wall",
                LocationType.WEREBEAR_AMULET,
            ),
            MMALocationData(
                "Wocka Wocka Werebear Amulet - On hill by lake",
                LocationType.WEREBEAR_AMULET,
            ),
            MMALocationData(
                "Wocka Wocka Werebear Amulet - On stairs near gardener",
                LocationType.WEREBEAR_AMULET,
            ),
            MMALocationData(
                "Muck Monster Amulet - Up climbable wall by Werebear Amulet",
                LocationType.MUCK_MONSTER_AMULET,
                [AbilityFlag.CLIMB],
            ),
            MMALocationData(
                "Muck Monster Amulet - Up climable wall above other Muck Monster Amulet",
                LocationType.MUCK_MONSTER_AMULET,
                [AbilityFlag.CLIMB],
            ),
            MMALocationData(
                "Muck Monster Amulet - Along the cliff trail",
                LocationType.MUCK_MONSTER_AMULET,
            ),
            MMALocationData(
                "Muck Monster Amulet - By the lake",
                LocationType.MUCK_MONSTER_AMULET,
            ),
            MMALocationData(
                "Noseferatu Amulet - Up Super Jump Pad",
                LocationType.NOSEFERATU_AMULET,
            ),
            MMALocationData(
                "Noseferatu Amulet - Bottom of the lake",
                LocationType.NOSEFERATU_AMULET,
                [AbilityFlag.SWIM],
            ),
            MMALocationData(
                "Noseferatu Amulet - Up stairs after triggering switch",
                LocationType.NOSEFERATU_AMULET,
                [AbilityFlag.GLOVE, AbilityFlag.GLIDE],
            ),
            MMALocationData(
                "Noseferatu Amulet - By sundial",
                LocationType.NOSEFERATU_AMULET,
            ),
            # Energy
            MMALocationData(
                "Evil Energy - 50%",
                LocationType.ENERGY,
                [AbilityFlag.GLOVE, AbilityFlag.SPIN, AbilityFlag.GLIDE, AbilityFlag.CLIMB, AbilityFlag.SWIM],
            ),
            MMALocationData(
                "Evil Energy - 100%",
                LocationType.ENERGY,
                [AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.SWIM | AbilityFlag.GLOVE | AbilityFlag.SPIN],
            ),
            # Tokens
            MMALocationData(
                "Muppet Token - By exit",
                LocationType.TOKEN,
            ),
            MMALocationData(
                "Muppet Token - Up Super Jump Pad",
                LocationType.TOKEN,
            ),
            MMALocationData(
                "Muppet Token - Race Percy",
                LocationType.TOKEN,
            ),
            MMALocationData(
                "Muppet Token - Sunflower minigame",
                LocationType.TOKEN,
                [AbilityFlag.GLIDE | AbilityFlag.CLIMB],
            ),
            MMALocationData(
                "Muppet Token - BONUS",
                LocationType.TOKEN,
                [AbilityFlag.GLIDE, AbilityFlag.GLOVE],
            ),
            # Bonus
            MMALocationData(
                "Bonus - B",
                LocationType.BONUS,
            ),
            MMALocationData(
                "Bonus - O",
                LocationType.BONUS,
            ),
            MMALocationData(
                "Bonus - N",
                LocationType.BONUS,
            ),
            MMALocationData(
                "Bonus - U",
                LocationType.BONUS,
            ),
            MMALocationData(
                "Bonus - S",
                LocationType.BONUS,
                [AbilityFlag.GLIDE, AbilityFlag.GLOVE],  # Bat switch platform
            ),
        ],
    ),
    MMARegion(
        LevelName.HALLWAYS_OF_DOOM,
        "CASTLE2",
        320,
        [
            # Amulets
            MMALocationData(
                "Ghoul-friend Amulet - Behind spawn",
                LocationType.GHOUL_FRIEND_AMULET,
            ),
            MMALocationData(
                "Ghoul-friend Amulet - On left staircase",
                LocationType.GHOUL_FRIEND_AMULET,
            ),
            MMALocationData(
                "Ghoul-friend Amulet - Top of left staircase",
                LocationType.GHOUL_FRIEND_AMULET,
            ),
            MMALocationData(
                "Ghoul-friend Amulet - Top of right staircase",
                LocationType.GHOUL_FRIEND_AMULET,
            ),
            # Energy
            MMALocationData(
                "Evil Energy - 50%",
                LocationType.ENERGY,
                [AbilityFlag.SMASH | AbilityFlag.GLOVE],  # Bat switch locks off like 70% of the level
            ),
            MMALocationData(
                "Evil Energy - 100%",
                LocationType.ENERGY,
                [AbilityFlag.SMASH | AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.SPIN],
            ),
            # Tokens
            MMALocationData(
                "Muppet Token - Rizzo",
                LocationType.TOKEN,
                [*any_weapon_flag(AbilityFlag.SMASH)],
            ),
            MMALocationData(
                "Muppet Token - On top of the bookshelves",
                LocationType.TOKEN,
                [AbilityFlag.SMASH | AbilityFlag.GLOVE | AbilityFlag.CLIMB],
            ),
            MMALocationData(
                "Muppet Token - Smashing minigame",
                LocationType.TOKEN,
                [AbilityFlag.SMASH | AbilityFlag.GLOVE],
            ),
            MMALocationData(
                "Muppet Token - Near smashable door",
                LocationType.TOKEN,
                [AbilityFlag.SMASH | AbilityFlag.GLOVE],
            ),
            MMALocationData(
                "Muppet Token - BONUS",
                LocationType.TOKEN,
                [AbilityFlag.SMASH | AbilityFlag.GLOVE | AbilityFlag.CLIMB | AbilityFlag.GLIDE],
            ),
            # Bonus
            MMALocationData(
                "Bonus - B",
                LocationType.BONUS,
                [AbilityFlag.SMASH],
            ),
            MMALocationData(
                "Bonus - O",
                LocationType.BONUS,
                [AbilityFlag.SMASH | AbilityFlag.CLIMB],
            ),
            MMALocationData(
                "Bonus - N",
                LocationType.BONUS,
                [AbilityFlag.SMASH | AbilityFlag.GLOVE],
            ),
            MMALocationData(
                "Bonus - U",
                LocationType.BONUS,
                [AbilityFlag.SMASH | AbilityFlag.GLOVE | AbilityFlag.CLIMB | AbilityFlag.GLIDE],
            ),
            MMALocationData(
                "Bonus - S",
                LocationType.BONUS,
                [AbilityFlag.SMASH | AbilityFlag.GLOVE],
            ),
        ],
    ),
    MMARegion(
        LevelName.POKER_FACES,
        "CASTLE3",
        350,
        [
            # Amulets
            MMALocationData(
                "Ker-monster Amulet - On lone pillar in lava",
                LocationType.KER_MONSTER_AMULET,
            ),
            MMALocationData(
                "Ker-monster Amulet - By search light towers",
                LocationType.KER_MONSTER_AMULET,
            ),
            MMALocationData(
                "Ker-monster Amulet - By pushable block",
                LocationType.KER_MONSTER_AMULET,
            ),
            MMALocationData(
                "Ker-monster Amulet - On trio of pillars in lava",
                LocationType.KER_MONSTER_AMULET,
            ),
            # Energy
            MMALocationData(
                "Evil Energy - 50%",
                LocationType.ENERGY,
                [AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE],
            ),
            MMALocationData(
                "Evil Energy - 100%",
                LocationType.ENERGY,
                [AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.CLIMB],
            ),
            # Tokens
            MMALocationData(
                "Muppet Token - Target shooting minigame",
                LocationType.TOKEN,
                [AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE],
            ),
            MMALocationData(
                "Muppet Token - Standing pillar by start",
                LocationType.TOKEN,
                [AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE],  # After shooting Beaker
            ),
            MMALocationData(
                "Muppet Token - Block minigame",
                LocationType.TOKEN,
                [AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.SPIN],
            ),
            MMALocationData(
                "Muppet Token - Glide to the rooftop",
                LocationType.TOKEN,
                [AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.CLIMB],
            ),
            MMALocationData(
                "Muppet Token - BONUS",
                LocationType.TOKEN,
                [AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.CLIMB],
            ),
            # Bonus
            MMALocationData(
                "Bonus - B",
                LocationType.BONUS,
            ),
            MMALocationData(
                "Bonus - O",
                LocationType.BONUS,
            ),
            MMALocationData(
                "Bonus - N",
                LocationType.BONUS,
                [AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE],
            ),
            MMALocationData(
                "Bonus - U",
                LocationType.BONUS,
                [AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.CLIMB],
            ),
            MMALocationData(
                "Bonus - S",
                LocationType.BONUS,
                [AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.CLIMB],
            ),
        ],
    ),
    MMABossRegion(
        LevelName.NOSEFERATU,
        "CASTLEB",
        [MMALocationData("Boss defeated", LocationType.BOSS, [AbilityFlag.GLOVE])],
    ),
]

# Maps region name to the region data definition
region_lookup: dict[str, MMARegion] = {region.name: region for region in all_locations_table}
non_boss_region_lookup: dict[str, MMARegion] = {
    region.name: region for region in all_locations_table if type(region) is MMARegion
}

# Lists all locations, by type
location_type_lookup: dict[LocationType, list[MMALocationData]] = {}
location_type_lookup_by_region: dict[str, dict[LocationType, list[MMALocationData]]] = {}
for region in all_locations_table:
    for loc in region.locations:
        location_type_lookup.update({loc.type: (location_type_lookup.get(loc.type) or []) + [loc]})
        # Store by region for level-based locations
        region_entry = location_type_lookup_by_region.get(region.name) or {}
        region_entry.update({loc.type: (region_entry.get(loc.type) or []) + [loc]})
        location_type_lookup_by_region.update({region.name: region_entry})

# Maps locations to their AP identifier
location_name_to_id: dict[str, int] = {}
__running_idx = 0
for region_data in all_locations_table:
    for location in region_data.locations:
        location.full_identifier = f"{region_data.name}: {location.name}"
        location_name_to_id.update({location.full_identifier: base_id + __running_idx})
        __running_idx += 1

# Groups locations by region
location_name_groups: dict[str, set[str]] = {}
for region_data in all_locations_table:
    location_name_groups[region_data.name] = {x.name for x in region_data.locations}
