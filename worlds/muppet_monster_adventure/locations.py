from enum import StrEnum


class Ability(StrEnum):
    CLIMB = "climb"
    SWIM = "swim"
    GLIDE = "glide"
    PUSH = "push"
    SMASH = "smash"
    # TODO: implement these
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

all_locations_table: dict[str, MMALocationData] = {**peacock_purgatory_locations}
