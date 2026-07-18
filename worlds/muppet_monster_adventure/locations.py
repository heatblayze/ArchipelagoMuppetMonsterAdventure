from enum import StrEnum


class Ability(StrEnum):
    CLIMB = "climb"
    SWIM = "swim"
    GLIDE = "glide"
    PUSH = "push"
    SMASH = "smash"


class MMALocationData:
    ability_requirements: list[Ability] | None

    def __init__(self, ability_requirements: list[Ability] | None = None):
        self.ability_requirements = ability_requirements


# TODO: Improve names?
peacock_purgatory_amulet_locations: dict[str, MMALocationData] = {
    "Wocka Wocka Werebear Amulet - By tutorial flags": MMALocationData(),
    "Wocka Wocka Werebear Amulet - On stairs near hedge trimmer": MMALocationData(),
    "Wocka Wocka Werebear Amulet - On hill by lake": MMALocationData(),
    "Wocka Wocka Werebear Amulet - By climbable wall": MMALocationData(),
}
