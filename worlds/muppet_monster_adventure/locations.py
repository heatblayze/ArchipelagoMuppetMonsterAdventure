from enum import StrEnum


class Ability(StrEnum):
    CLIMB = "climb"
    SWIM = "swim"
    GLIDE = "glide"
    PUSH = "push"
    SMASH = "smash"
    # TODO: implement these (if possible)
    GLOVE = "glove"
    SPIN = "spin"


class MMALocationData:
    ability_requirements: list[Ability] | None

    def __init__(self, ability_requirements: list[Ability] | None = None):
        self.ability_requirements = ability_requirements


# TODO: Improve names
peacock_purgatory_amulet_locations: dict[str, MMALocationData] = {
    "Wocka Wocka Werebear Amulet - By tutorial flags": MMALocationData(),
    "Wocka Wocka Werebear Amulet - On stairs near gardener": MMALocationData(),
    "Wocka Wocka Werebear Amulet - On hill by lake": MMALocationData(),
    "Wocka Wocka Werebear Amulet - By climbable wall": MMALocationData(),
    "Muck Monster Amulet - By the lake": MMALocationData(),
    "Muck Monster Amulet - Up climbable wall by Werebear Amulet": MMALocationData([Ability.CLIMB]),
    "Muck Monster Amulet - On path before climable wall": MMALocationData(),
    "Muck Monster Amulet - Up climable wall by Muck Monster Amulet": MMALocationData([Ability.CLIMB]),
    "Noseferatu Amulet - Bottom of the lake": MMALocationData([Ability.SWIM]),
    "Noseferatu Amulet - By sundial": MMALocationData(),
    "Noseferatu Amulet - Up super-jump platform": MMALocationData(),
    "Noseferatu Amulet - Up stairs after triggering switch": MMALocationData([Ability.GLOVE]),
}

peacock_purgatory_locations: dict[str, MMALocationData] = {**peacock_purgatory_amulet_locations}

# TODO: other regions

all_locations_table: dict[str, dict[str, MMALocationData]] = {
    "Peacock Purgatory": peacock_purgatory_locations,
}


def location_name_to_id(base_id: int) -> dict[str, int]:
    """Converts all locations from their `[Region: [Name: Data]]` format into `[Name: ID]`,
    where `ID` is a deterministic value greater than `base_id`."""
    result: dict[str, int] = {}
    for group_idx, region_data in enumerate(all_locations_table.values()):
        for item_idx, loc_name in enumerate(region_data):
            result.update({loc_name: base_id + group_idx + item_idx})
    return result


def location_name_groups() -> dict[str, set[str]]:
    """Converts all locations from their `[Region: [Name: Data]]` format into `[Region: [Name]]`."""
    result: dict[str, set[str]] = {}
    for region_name, region_data in all_locations_table.items():
        result[region_name] = set(region_data.keys())
    return result
