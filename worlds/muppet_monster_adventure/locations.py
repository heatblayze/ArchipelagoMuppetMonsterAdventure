from collections.abc import Sequence
from enum import Enum, StrEnum
from typing import NamedTuple

from .shared import AbilityFlag, AmuletType, LevelName, any_weapon_flag, base_id, flag_variants


class LocationType(Enum):
    NOSEFERATU_AMULET = AmuletType.NOSEFERATU_AMULET.value
    WEREBEAR_AMULET = AmuletType.WEREBEAR_AMULET.value
    KER_MONSTER_AMULET = AmuletType.KER_MONSTER_AMULET.value
    MUCK_MONSTER_AMULET = AmuletType.MUCK_MONSTER_AMULET.value
    GHOUL_FRIEND_AMULET = AmuletType.GHOUL_FRIEND_AMULET.value
    ENERGY = "Evil Energy"
    TOKEN = "Muppet Token"
    BONUS = "Bonus letter"
    BOSS = "Boss defeated"


class MMALocationData:
    ability_requirements: list[AbilityFlag] | None

    def __init__(
        self,
        type: LocationType,
        name: str,
        ability_requirements: list[AbilityFlag] | None = None,
    ):
        self.name: str = name
        self.type: LocationType = type
        # Each flag lists the unique combination of abilities which unlocks this location.
        # Alternatives should be provided as a separate entry.
        # e.g. The location can be unlocked by either "climb and swim" OR "climb and glide".
        # This would be represented as: [AbilityFlag.CLIMB | AbilityFlag.SWIM, AbilityFlag.CLIMB | AbilityFlag.GLIDE]
        self.ability_requirements = (
            ability_requirements if ability_requirements is not None and len(ability_requirements) > 0 else None
        )
        self.full_identifier: str = ""

    def ap_id(self) -> int:
        return location_name_to_id[self.full_identifier]


class MMABossLocationData(MMALocationData):
    def __init__(
        self,
        ability_requirements: list[AbilityFlag] | None = None,
    ):
        super().__init__(LocationType.BOSS, LocationType.BOSS.value, ability_requirements)

    def get_event_name(self) -> str:
        return f"{self.full_identifier} event"


class EnergyAmount(StrEnum):
    HALF = "50%"
    FULL = "100%"


class MMAEnergyLocationData(MMALocationData):
    def __init__(
        self,
        amount: EnergyAmount,
        ability_requirements: list[AbilityFlag] | None = None,
    ):
        super().__init__(LocationType.ENERGY, f"{LocationType.ENERGY.value} - {amount.value}", ability_requirements)


class BonusLetterType(StrEnum):
    B = "B"
    O = "O"
    N = "N"
    U = "U"
    S = "S"


class MMABonusLetterLocationData(MMALocationData):
    def __init__(
        self,
        letter: BonusLetterType,
        ability_requirements: list[AbilityFlag] | None = None,
    ):
        super().__init__(LocationType.BONUS, f"{LocationType.BONUS.value} - {letter.value}", ability_requirements)


class MMAMuppetTokenLocationData(MMALocationData):
    def __init__(
        self,
        name: str,
        ability_requirements: list[AbilityFlag] | None = None,
    ):
        super().__init__(LocationType.TOKEN, f"{LocationType.TOKEN.value} - {name}", ability_requirements)


class MMAAmuletLocationData(MMALocationData):
    def __init__(
        self,
        type: AmuletType,
        name: str,
        ability_requirements: list[AbilityFlag] | None = None,
    ):
        location_type = LocationType(type.value)
        super().__init__(location_type, f"{type.value} - {name}", ability_requirements)


class MMARegion:
    def __init__(
        self,
        name: LevelName,
        ingame_identifier: str,
        energy_count: int,
        locations: list[MMALocationData],
    ) -> None:
        self.name: str = name.value
        self.ingame_identifier: str = ingame_identifier
        self.energy_count: int = energy_count
        self.locations: list[MMALocationData] = locations
        pass


class EnergyLocationData(NamedTuple):
    half: list[AbilityFlag] | None
    full: list[AbilityFlag] | None


class BonusLocationData(NamedTuple):
    b: list[AbilityFlag] | None
    o: list[AbilityFlag] | None
    n: list[AbilityFlag] | None
    u: list[AbilityFlag] | None
    s: list[AbilityFlag] | None
    # We may not always be able to infer the requirements for this, since it could be off the path
    # and logic changes / new rules could make this different to just all letters combined.
    # TODO: the generated rules for this should include the ability to get all the letters
    token: list[AbilityFlag] | None


class TokenLocationData(NamedTuple):
    name: str
    requirements: list[AbilityFlag] | None = None


class LevelRegionData(NamedTuple):
    name: LevelName
    total_energy: int
    energy: EnergyLocationData
    bonus: BonusLocationData
    # TODO: figure out a nice way to enforce index parity with the memory addresses...
    tokens: list[TokenLocationData]
    # TODO: make amulets their own location type, instead of this.
    extra_locations: Sequence[MMALocationData] | None = None


class MMALevelRegion(MMARegion):
    def __init__(
        self,
        ingame_identifier: str,
        data: LevelRegionData,
    ) -> None:
        locations: list[MMALocationData] = [
            *[
                MMAEnergyLocationData(EnergyAmount.HALF, data.energy.half),
                MMAEnergyLocationData(EnergyAmount.FULL, data.energy.full),
            ],
            *[
                MMABonusLetterLocationData(BonusLetterType.B, data.bonus.b),
                MMABonusLetterLocationData(BonusLetterType.O, data.bonus.o),
                MMABonusLetterLocationData(BonusLetterType.N, data.bonus.n),
                MMABonusLetterLocationData(BonusLetterType.U, data.bonus.u),
                MMABonusLetterLocationData(BonusLetterType.S, data.bonus.s),
            ],
            *[
                MMAMuppetTokenLocationData(token.name, token.requirements)
                for token in [*data.tokens, TokenLocationData("BONUS", data.bonus.token)]  # Append the bonus token
            ],
            *(data.extra_locations if data.extra_locations is not None else []),
        ]
        super().__init__(data.name, ingame_identifier, data.total_energy, locations)
        pass


class BossRegionData(NamedTuple):
    name: LevelName
    completion_requirements: list[AbilityFlag] | None


class MMABossRegion(MMARegion):
    def __init__(
        self,
        ingame_identifier: str,
        data: BossRegionData,
    ) -> None:
        super().__init__(data.name, ingame_identifier, 0, [MMABossLocationData(data.completion_requirements)])


# TODO: currently we're assuming checks can be done without caring about taking damage
# The iframes are very lenient, allowing you to get past basically every enemy,
# and the levels tend to have a good number of recovery hearts.
# BUT!! (and this is a big BUTT) the game does get notably harder to play this way after zone 1.
# Playtesting is required here...
# Note: for zone 2 onwards I have included killing enemies which block the path as a requirement.


# All level groups share the same structure:
# - Always three levels and then a boss
# - All levels start with the same prefix
# - Regular levels have the suffix of their (1-based) relative level number
# - Boss levels are suffixed by the letter B
class LevelGroup:
    def __init__(
        self,
        identifier: str,
        one: LevelRegionData,
        two: LevelRegionData,
        three: LevelRegionData,
        boss: BossRegionData,
    ) -> None:
        self.one: MMALevelRegion = MMALevelRegion(f"{identifier}1", one)
        self.two: MMALevelRegion = MMALevelRegion(f"{identifier}2", two)
        self.three: MMALevelRegion = MMALevelRegion(f"{identifier}3", three)
        self.boss: MMABossRegion = MMABossRegion(f"{identifier}B", boss)
        pass

    def flatten(self) -> Sequence[MMARegion]:
        return [self.one, self.two, self.three, self.boss]


# Note: The order of basically all of these matters, since the client depends on this to check world state.
level_groups: list[LevelGroup] = [
    LevelGroup(
        identifier="CASTLE",
        one=LevelRegionData(
            name=LevelName.PEACOCK_PURGATORY,
            total_energy=300,
            energy=EnergyLocationData(
                half=[AbilityFlag.GLOVE, AbilityFlag.SPIN, AbilityFlag.GLIDE, AbilityFlag.CLIMB, AbilityFlag.SWIM],
                full=[AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.SWIM | AbilityFlag.GLOVE | AbilityFlag.SPIN],
            ),
            bonus=BonusLocationData(
                b=None,
                o=None,
                n=None,
                u=None,
                s=[AbilityFlag.GLIDE, AbilityFlag.GLOVE],  # Bat switch platform
                token=[AbilityFlag.GLIDE, AbilityFlag.GLOVE],
            ),
            tokens=[
                TokenLocationData("By exit"),
                TokenLocationData("Up Super Jump Pad"),
                TokenLocationData("Race Percy"),
                TokenLocationData("Sunflower minigame", [AbilityFlag.GLIDE | AbilityFlag.CLIMB]),
            ],
            extra_locations=[
                # Note: these are ordered by their bitwise flag position (per type)
                # Werebear
                MMAAmuletLocationData(AmuletType.WEREBEAR_AMULET, "By tutorial flags"),
                MMAAmuletLocationData(AmuletType.WEREBEAR_AMULET, "By climbable wall"),
                MMAAmuletLocationData(AmuletType.WEREBEAR_AMULET, "On hill by lake"),
                MMAAmuletLocationData(AmuletType.WEREBEAR_AMULET, "On stairs near gardener"),
                # Muck Monster
                MMAAmuletLocationData(
                    AmuletType.MUCK_MONSTER_AMULET, "Up climbable wall by Werebear Amulet", [AbilityFlag.CLIMB]
                ),
                MMAAmuletLocationData(
                    AmuletType.MUCK_MONSTER_AMULET,
                    "Up climable wall above other Muck Monster Amulet",
                    [AbilityFlag.CLIMB],
                ),
                MMAAmuletLocationData(AmuletType.MUCK_MONSTER_AMULET, "Along the cliff trail"),
                MMAAmuletLocationData(AmuletType.MUCK_MONSTER_AMULET, "By the lake"),
                # Noseferatu
                MMAAmuletLocationData(AmuletType.NOSEFERATU_AMULET, "Up Super Jump Pad"),
                MMAAmuletLocationData(AmuletType.NOSEFERATU_AMULET, "Bottom of the lake", [AbilityFlag.SWIM]),
                MMAAmuletLocationData(
                    AmuletType.NOSEFERATU_AMULET,
                    "Up stairs after triggering switch",
                    [AbilityFlag.GLOVE, AbilityFlag.GLIDE],
                ),
                MMAAmuletLocationData(AmuletType.NOSEFERATU_AMULET, "By sundial"),
            ],
        ),
        two=LevelRegionData(
            name=LevelName.HALLWAYS_OF_DOOM,
            total_energy=320,
            energy=EnergyLocationData(
                half=[AbilityFlag.SMASH | AbilityFlag.GLOVE],  # Bat switch locks off like 70% of the level
                full=[AbilityFlag.SMASH | AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.SPIN],
            ),
            bonus=BonusLocationData(
                b=[AbilityFlag.SMASH],
                o=[AbilityFlag.SMASH | AbilityFlag.CLIMB],
                n=[AbilityFlag.SMASH | AbilityFlag.GLOVE],
                u=[AbilityFlag.SMASH | AbilityFlag.GLOVE | AbilityFlag.CLIMB | AbilityFlag.GLIDE],
                s=[AbilityFlag.SMASH | AbilityFlag.GLOVE],
                token=[AbilityFlag.SMASH | AbilityFlag.GLOVE | AbilityFlag.CLIMB | AbilityFlag.GLIDE],
            ),
            tokens=[
                TokenLocationData("Catch Rizzo", any_weapon_flag(AbilityFlag.SMASH)),
                TokenLocationData(
                    "On top of the bookshelves", [AbilityFlag.SMASH | AbilityFlag.GLOVE | AbilityFlag.CLIMB]
                ),
                TokenLocationData("Smashing minigame", [AbilityFlag.SMASH | AbilityFlag.GLOVE]),
                TokenLocationData("Near smashable door", [AbilityFlag.SMASH | AbilityFlag.GLOVE]),
            ],
            extra_locations=[
                # Amulets
                MMAAmuletLocationData(AmuletType.GHOUL_FRIEND_AMULET, "Behind spawn"),
                MMAAmuletLocationData(AmuletType.GHOUL_FRIEND_AMULET, "On left staircase"),
                MMAAmuletLocationData(AmuletType.GHOUL_FRIEND_AMULET, "Top of left staircase"),
                MMAAmuletLocationData(AmuletType.GHOUL_FRIEND_AMULET, "Top of right staircase"),
            ],
        ),
        three=LevelRegionData(
            name=LevelName.POKER_FACES,
            total_energy=350,
            energy=EnergyLocationData(
                half=[AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE],
                full=[AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.CLIMB],
            ),
            bonus=BonusLocationData(
                b=None,
                o=None,
                n=[AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE],
                u=[AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.CLIMB],
                s=[AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.CLIMB],
                token=[AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.CLIMB],
            ),
            tokens=[
                TokenLocationData(
                    "Target shooting minigame", [AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE]
                ),
                TokenLocationData(
                    "Standing pillar by start", [AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE]
                ),
                TokenLocationData(
                    "Block minigame", [AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.SPIN]
                ),
                TokenLocationData(
                    "Glide to the rooftop",
                    [AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.CLIMB],
                ),
            ],
            extra_locations=[
                # Amulets
                MMAAmuletLocationData(AmuletType.KER_MONSTER_AMULET, "On lone pillar in lava"),
                MMAAmuletLocationData(AmuletType.KER_MONSTER_AMULET, "By search light towers"),
                MMAAmuletLocationData(AmuletType.KER_MONSTER_AMULET, "By pushable block"),
                MMAAmuletLocationData(AmuletType.KER_MONSTER_AMULET, "On trio of pillars in lava"),
            ],
        ),
        boss=BossRegionData(LevelName.NOSEFERATU_BITES_BACK, [AbilityFlag.GLOVE]),
    ),
    LevelGroup(
        identifier="GRVYARD",
        one=LevelRegionData(
            name=LevelName.GRAVE_MATTERS,
            total_energy=250,
            energy=EnergyLocationData(
                half=[
                    AbilityFlag.GLOVE | AbilityFlag.SPIN,
                    AbilityFlag.GLOVE | AbilityFlag.GLIDE,
                ],
                full=[
                    AbilityFlag.ALL_WEAPONS | AbilityFlag.GLIDE | AbilityFlag.SWIM,
                ],
            ),
            bonus=BonusLocationData(
                b=[AbilityFlag.GLOVE | AbilityFlag.GLIDE],
                o=[AbilityFlag.GLOVE | AbilityFlag.GLIDE],
                n=[AbilityFlag.GLOVE | AbilityFlag.GLIDE],
                u=[AbilityFlag.GLOVE | AbilityFlag.GLIDE],
                s=[AbilityFlag.GLOVE | AbilityFlag.GLIDE | AbilityFlag.SWIM],
                token=[AbilityFlag.GLOVE | AbilityFlag.GLIDE | AbilityFlag.SWIM],
            ),
            tokens=[
                TokenLocationData("Catch Rizzo", any_weapon_flag()),
                TokenLocationData("On pillar near Rizzo", [AbilityFlag.PUSH]),
                TokenLocationData(
                    "Skull memory minigame",
                    [AbilityFlag.GLOVE | AbilityFlag.GLIDE | AbilityFlag.SPIN],
                ),
                TokenLocationData(
                    "Hidden underwater tunnel",
                    [AbilityFlag.GLOVE | AbilityFlag.GLIDE | AbilityFlag.SWIM],
                ),
            ],
        ),
        two=LevelRegionData(
            name=LevelName.MOLTEN_MAYHEM,
            total_energy=380,
            energy=EnergyLocationData(
                half=[AbilityFlag.GLOVE | AbilityFlag.GLIDE],
                full=[AbilityFlag.ALL_WEAPONS | AbilityFlag.GLIDE | AbilityFlag.CLIMB | AbilityFlag.SMASH],
            ),
            bonus=BonusLocationData(
                b=[AbilityFlag.GLOVE],
                o=[AbilityFlag.GLOVE | AbilityFlag.GLIDE],
                n=[AbilityFlag.GLOVE | AbilityFlag.GLIDE | AbilityFlag.SMASH],
                u=[AbilityFlag.GLOVE | AbilityFlag.GLIDE],
                s=[AbilityFlag.GLOVE | AbilityFlag.GLIDE],
                token=[AbilityFlag.GLOVE | AbilityFlag.GLIDE | AbilityFlag.SMASH],
            ),
            tokens=[
                TokenLocationData("Target shooting minigame", [AbilityFlag.GLOVE]),
                TokenLocationData("Ghost hunting", [AbilityFlag.ALL_WEAPONS | AbilityFlag.GLIDE | AbilityFlag.CLIMB]),
                TokenLocationData("Walk along the wall", [AbilityFlag.GLOVE | AbilityFlag.GLIDE]),
                TokenLocationData("Hidden room near start", [AbilityFlag.GLOVE | AbilityFlag.GLIDE]),
            ],
        ),
        three=LevelRegionData(
            name=LevelName.SHIVERING_TIMBER_SHOALS,
            total_energy=400,
            energy=EnergyLocationData(
                half=[AbilityFlag.ALL_WEAPONS | AbilityFlag.GLIDE],
                full=[AbilityFlag.ALL_WEAPONS | AbilityFlag.GLIDE | AbilityFlag.SMASH | AbilityFlag.PUSH],
            ),
            bonus=BonusLocationData(
                b=[AbilityFlag.GLIDE],
                o=[AbilityFlag.ALL_WEAPONS | AbilityFlag.GLIDE],
                n=[AbilityFlag.ALL_WEAPONS | AbilityFlag.GLIDE],
                u=[AbilityFlag.ALL_WEAPONS | AbilityFlag.GLIDE],
                s=[AbilityFlag.ALL_WEAPONS | AbilityFlag.GLIDE],
                token=[AbilityFlag.ALL_WEAPONS | AbilityFlag.GLIDE],
            ),
            tokens=[
                TokenLocationData("Shell collecting", [AbilityFlag.GLIDE | AbilityFlag.GLOVE]),
                TokenLocationData(
                    "Smashable wall next to Shell Pirate",
                    [AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.SMASH | AbilityFlag.PUSH],
                ),
                TokenLocationData("Super Jump after the sunken ship", [AbilityFlag.ALL_WEAPONS | AbilityFlag.GLIDE]),
                TokenLocationData("Race Simon", [AbilityFlag.ALL_WEAPONS | AbilityFlag.GLIDE]),
            ],
        ),
        boss=BossRegionData(LevelName.BEE_WARE_THE_WEREBEAR, [AbilityFlag.SPIN]),
    ),
    LevelGroup(
        identifier="FOREST",
        one=LevelRegionData(
            name=LevelName.HIKE_OF_THE_HAUNTED,
            total_energy=400,
            energy=EnergyLocationData(
                half=[AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.GLOVE],
                full=[AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.ALL_WEAPONS],
            ),
            bonus=BonusLocationData(
                b=[AbilityFlag.CLIMB | AbilityFlag.GLIDE],
                o=[AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.GLOVE],
                n=[AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.GLOVE],
                u=[AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.GLOVE],
                s=[AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.GLOVE],
                token=[AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.GLOVE],
            ),
            tokens=[
                TokenLocationData("Next to big climbable tree", [AbilityFlag.CLIMB | AbilityFlag.GLIDE]),
                TokenLocationData(
                    "Follow the floating Super Jump Pads", [AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.GLOVE]
                ),
                TokenLocationData("Totem hunting", [AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.GLOVE]),
                TokenLocationData("Gliding minigame", [AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.GLOVE]),
                TokenLocationData("Near gliding minigame", [AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.GLOVE]),
            ],
        ),
        two=LevelRegionData(
            name=LevelName.THE_RIVER_VILE,
            total_energy=420,
            energy=EnergyLocationData(
                half=flag_variants(
                    AbilityFlag.GLIDE | AbilityFlag.SMASH,
                    AbilityFlag.ALL_WEAPONS,
                    *any_weapon_flag(AbilityFlag.CLIMB),
                ),
                full=[AbilityFlag.GLIDE | AbilityFlag.SMASH | AbilityFlag.ALL_WEAPONS | AbilityFlag.CLIMB],
            ),
            bonus=BonusLocationData(
                b=[AbilityFlag.GLIDE | AbilityFlag.SMASH | AbilityFlag.CLIMB],
                o=[AbilityFlag.GLIDE | AbilityFlag.SMASH | AbilityFlag.CLIMB],
                n=[AbilityFlag.GLIDE | AbilityFlag.SMASH],
                u=[AbilityFlag.GLIDE | AbilityFlag.SMASH | AbilityFlag.CLIMB],
                s=[AbilityFlag.GLIDE | AbilityFlag.SMASH | AbilityFlag.CLIMB | AbilityFlag.GLOVE],
                token=[AbilityFlag.GLIDE | AbilityFlag.SMASH | AbilityFlag.CLIMB | AbilityFlag.GLOVE],
            ),
            tokens=[
                TokenLocationData(
                    "Climb near the first checkpoint", [AbilityFlag.GLIDE | AbilityFlag.SMASH | AbilityFlag.CLIMB]
                ),
                TokenLocationData("Catch Rizzo", any_weapon_flag(AbilityFlag.GLIDE | AbilityFlag.SMASH)),
                TokenLocationData(
                    "Atop the machine near Rizzo", [AbilityFlag.GLIDE | AbilityFlag.SMASH | AbilityFlag.CLIMB]
                ),
                TokenLocationData("Cog spinning minigame", [AbilityFlag.GLIDE | AbilityFlag.SMASH | AbilityFlag.SPIN]),
                TokenLocationData(
                    "Shoot Beaker", [AbilityFlag.GLIDE | AbilityFlag.SMASH | AbilityFlag.CLIMB | AbilityFlag.GLOVE]
                ),
            ],
        ),
        three=LevelRegionData(
            name=LevelName.ESCAPE_CLAWS,
            total_energy=450,
            energy=EnergyLocationData(
                half=[AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.GLOVE],
                full=[AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.PUSH | AbilityFlag.ALL_WEAPONS],
            ),
            bonus=BonusLocationData(
                b=[AbilityFlag.CLIMB | AbilityFlag.GLIDE],
                o=[AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.GLOVE],
                n=[AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.GLOVE],
                u=[AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.PUSH],
                s=[AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.PUSH],
                token=[AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.PUSH],
            ),
            tokens=[
                TokenLocationData("Climbing minigame", [AbilityFlag.CLIMB]),
                TokenLocationData("Near bat switch", [AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.GLOVE]),
                TokenLocationData("Near BONUS crate", [AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.GLOVE]),
                TokenLocationData(
                    "Race Willie", [AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.PUSH]
                ),
                TokenLocationData(
                    "After Willie", [AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.PUSH]
                ),
            ],
        ),
        boss=BossRegionData(LevelName.COWER_BEFORE_KER_MONSTER, [AbilityFlag.GLOVE]),
    ),
    LevelGroup(
        identifier="VILLAGE",
        one=LevelRegionData(
            name=LevelName.CROAK_LAHOMA,
            total_energy=450,
            energy=EnergyLocationData(
                half=[AbilityFlag.PUSH | AbilityFlag.GLOVE],
                full=[AbilityFlag.PUSH | AbilityFlag.ALL_WEAPONS | AbilityFlag.SMASH | AbilityFlag.GLIDE],
            ),
            bonus=BonusLocationData(
                b=[AbilityFlag.GLIDE],
                o=None,
                n=[AbilityFlag.PUSH | AbilityFlag.GLOVE],
                u=[AbilityFlag.PUSH | AbilityFlag.GLOVE],
                s=[AbilityFlag.PUSH | AbilityFlag.GLOVE],
                token=[AbilityFlag.PUSH | AbilityFlag.GLOVE | AbilityFlag.GLIDE],
            ),
            tokens=[
                TokenLocationData("Near BONUS letter O", [AbilityFlag.GLIDE]),
                TokenLocationData("Ghost hunting", [AbilityFlag.PUSH | AbilityFlag.ALL_WEAPONS]),
                TokenLocationData("Guarded by an evil scarecrow", [AbilityFlag.PUSH | AbilityFlag.GLOVE]),
                TokenLocationData("By a pink barrel", [AbilityFlag.PUSH | AbilityFlag.GLOVE]),
                TokenLocationData("Smash the water things", [AbilityFlag.PUSH | AbilityFlag.GLOVE | AbilityFlag.SMASH]),
            ],
        ),
        two=LevelRegionData(
            name=LevelName.ARABIAN_FRIGHTS,
            total_energy=480,
            energy=EnergyLocationData(
                half=[AbilityFlag.ALL_WEAPONS | AbilityFlag.CLIMB | AbilityFlag.PUSH],
                full=[AbilityFlag.ALL_WEAPONS | AbilityFlag.CLIMB | AbilityFlag.PUSH | AbilityFlag.GLIDE],
            ),
            bonus=BonusLocationData(
                b=None,
                o=flag_variants(AbilityFlag.GLOVE | AbilityFlag.CLIMB, AbilityFlag.PUSH, AbilityFlag.GLIDE),
                n=[AbilityFlag.GLOVE | AbilityFlag.CLIMB | AbilityFlag.PUSH | AbilityFlag.GLIDE],
                u=[AbilityFlag.ALL_WEAPONS | AbilityFlag.CLIMB],
                s=[AbilityFlag.ALL_WEAPONS | AbilityFlag.CLIMB | AbilityFlag.GLIDE],
                token=[AbilityFlag.ALL_WEAPONS | AbilityFlag.CLIMB | AbilityFlag.PUSH | AbilityFlag.GLIDE],
            ),
            tokens=[
                TokenLocationData(
                    "On a hidden ledge near rolling barrels",
                    flag_variants(AbilityFlag.GLOVE | AbilityFlag.CLIMB, AbilityFlag.PUSH, AbilityFlag.GLIDE),
                ),
                TokenLocationData(
                    "Snake catching",
                    flag_variants(AbilityFlag.GLOVE | AbilityFlag.CLIMB, AbilityFlag.PUSH, AbilityFlag.GLIDE),
                ),
                TokenLocationData(
                    "Above a pushable crate",
                    [AbilityFlag.GLOVE | AbilityFlag.CLIMB | AbilityFlag.PUSH | AbilityFlag.GLIDE],
                ),
                TokenLocationData(
                    "On a hidden ledge near pushable crates",
                    [AbilityFlag.ALL_WEAPONS | AbilityFlag.CLIMB | AbilityFlag.PUSH],
                ),
                TokenLocationData(
                    "Race Percy",
                    [AbilityFlag.ALL_WEAPONS | AbilityFlag.CLIMB | AbilityFlag.PUSH],
                ),
            ],
        ),
        three=LevelRegionData(
            name=LevelName.FEELING_FLUSHED,
            total_energy=500,
            energy=EnergyLocationData(
                half=[AbilityFlag.GLOVE | AbilityFlag.GLIDE | AbilityFlag.PUSH],
                full=[AbilityFlag.ALL_WEAPONS | AbilityFlag.GLIDE | AbilityFlag.PUSH | AbilityFlag.SWIM],
            ),
            bonus=BonusLocationData(
                # Is technically *meant* to require swim, but the "trick" is not only
                # incredibly easy but incredibly obvious as well.
                b=None,
                o=[AbilityFlag.GLOVE | AbilityFlag.GLIDE | AbilityFlag.PUSH],
                n=[AbilityFlag.GLOVE | AbilityFlag.GLIDE | AbilityFlag.PUSH],
                u=[AbilityFlag.GLOVE | AbilityFlag.GLIDE | AbilityFlag.PUSH],
                s=[AbilityFlag.GLOVE | AbilityFlag.GLIDE | AbilityFlag.PUSH | AbilityFlag.SWIM],
                token=[AbilityFlag.GLOVE | AbilityFlag.GLIDE | AbilityFlag.PUSH | AbilityFlag.SWIM],
            ),
            tokens=[
                TokenLocationData(
                    "In a crack in a pipe",
                    [AbilityFlag.GLOVE | AbilityFlag.GLIDE],
                ),
                TokenLocationData(
                    "Near BONUS letter 0",
                    [AbilityFlag.GLOVE | AbilityFlag.GLIDE | AbilityFlag.PUSH],
                ),
                TokenLocationData(
                    "Pushing puzzle",
                    [AbilityFlag.GLOVE | AbilityFlag.GLIDE | AbilityFlag.PUSH],
                ),
                TokenLocationData(
                    "Catch Rizzo",
                    [AbilityFlag.GLOVE | AbilityFlag.GLIDE | AbilityFlag.PUSH],
                ),
                TokenLocationData(
                    "Above Rizzo",
                    [AbilityFlag.GLOVE | AbilityFlag.GLIDE | AbilityFlag.PUSH],
                ),
            ],
        ),
        boss=BossRegionData(LevelName.THE_MUCK_MONSTER_SLIMETH, None),  # wow
    ),
    LevelGroup(
        identifier="SWAMP",
        one=LevelRegionData(
            name=LevelName.HUT_HUT_HIKE,
            total_energy=500,
            energy=EnergyLocationData(
                # Nothing: 71
                # Spin: +24 (95)
                # Glove: +38 (109)
                # Swim: +146 (217)
                # Smash: +6 (77)
                # Smash+Spin: +48 (119)
                half=flag_variants(
                    AbilityFlag.SWIM,
                    AbilityFlag.GLOVE,
                    AbilityFlag.SMASH | AbilityFlag.SPIN,
                ),
                full=[AbilityFlag.ALL_WEAPONS | AbilityFlag.SMASH | AbilityFlag.SWIM],
            ),
            bonus=BonusLocationData(
                b=None,
                o=[AbilityFlag.SMASH],
                n=None,
                u=[AbilityFlag.ALL_WEAPONS | AbilityFlag.SWIM],
                s=[AbilityFlag.SWIM],
                token=[AbilityFlag.ALL_WEAPONS | AbilityFlag.SWIM | AbilityFlag.SMASH],
            ),
            tokens=[
                TokenLocationData(
                    "Behind the start",
                    None,
                ),
                TokenLocationData(
                    "Inside a smashable hut",
                    [AbilityFlag.SMASH],
                ),
                TokenLocationData(
                    "In the pufferfish-filled tunnel",
                    [AbilityFlag.SWIM],
                ),
                TokenLocationData(
                    "Race the Shark",
                    [AbilityFlag.SWIM],
                ),
                TokenLocationData(
                    "Guarded by an enemy inside a smashable hut",
                    [AbilityFlag.ALL_WEAPONS | AbilityFlag.SWIM | AbilityFlag.SMASH],
                ),
                TokenLocationData(
                    "Gather ingredients for soup",
                    [AbilityFlag.ALL_WEAPONS | AbilityFlag.SWIM | AbilityFlag.GLIDE],
                ),
            ],
        ),
        two=LevelRegionData(
            name=LevelName.TEMPLE_OF_PORK,
            total_energy=520,
            energy=EnergyLocationData(
                half=[AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.SWIM],
                full=[AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.ALL_WEAPONS | AbilityFlag.SWIM],
            ),
            bonus=BonusLocationData(
                b=None,
                o=[AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.SWIM],
                n=[AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.SWIM],
                u=[AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.SWIM],
                s=[AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.SWIM],
                token=[AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.SWIM],
            ),
            tokens=[
                TokenLocationData(
                    "Above the swimming tunnel",
                    [AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.SWIM],
                ),
                TokenLocationData(
                    "On a hanging platform above the swimming tunnel",
                    [AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.SWIM],
                ),
                TokenLocationData(
                    "Block pushing puzzle",
                    [AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.ALL_WEAPONS | AbilityFlag.SWIM],
                ),
                TokenLocationData(
                    "Hunt the Golden Statues",
                    [AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.SWIM],
                ),
                TokenLocationData(
                    "Next to the statue hunting minigame",
                    [AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.SWIM],
                ),
                TokenLocationData(
                    "Next to BONUS letter S",
                    [AbilityFlag.PUSH | AbilityFlag.GLIDE | AbilityFlag.GLOVE | AbilityFlag.SWIM],
                ),
            ],
        ),
        three=LevelRegionData(
            name=LevelName.THE_BLUEST_BAYOU,
            total_energy=550,
            energy=EnergyLocationData(
                half=[AbilityFlag.GLOVE | AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.SWIM],
                full=[AbilityFlag.ALL_WEAPONS | AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.SWIM],
            ),
            bonus=BonusLocationData(
                b=[AbilityFlag.SWIM],
                o=[],
                n=[AbilityFlag.GLOVE | AbilityFlag.CLIMB | AbilityFlag.GLIDE],
                u=[AbilityFlag.GLOVE | AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.SWIM],
                s=[AbilityFlag.SWIM],
                token=[AbilityFlag.GLOVE | AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.SWIM],
            ),
            tokens=[
                TokenLocationData(
                    "In the bayou?",
                    [AbilityFlag.GLOVE | AbilityFlag.CLIMB | AbilityFlag.GLIDE],
                ),
                TokenLocationData(
                    "Above the BONUS letter S",
                    [AbilityFlag.SWIM | AbilityFlag.CLIMB],
                ),
                TokenLocationData(
                    "Catch Rizzo",
                    [AbilityFlag.GLOVE | AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.SWIM],
                ),
                TokenLocationData(
                    "Above the steaming cauldron",
                    [AbilityFlag.GLOVE | AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.SWIM],
                ),
                TokenLocationData(
                    "Pearl hunting",
                    [AbilityFlag.GLOVE | AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.SWIM],
                ),
                TokenLocationData(
                    "Sitting on a stump",
                    [AbilityFlag.GLOVE | AbilityFlag.CLIMB | AbilityFlag.GLIDE | AbilityFlag.SWIM],
                ),
            ],
        ),
        boss=BossRegionData(LevelName.DOIN_THE_BRIDE_SLIDE, None),  # incredible
    ),
    LevelGroup(
        identifier="ICEMONT",
        one=LevelRegionData(
            name=LevelName.THE_MONSTERY_MONASTERY,
            total_energy=550,
            energy=EnergyLocationData(
                half=[AbilityFlag.GLOVE],
                full=[AbilityFlag.ALL_WEAPONS | AbilityFlag.SMASH | AbilityFlag.GLIDE | AbilityFlag.SWIM],
            ),
            bonus=BonusLocationData(
                b=[AbilityFlag.SWIM],
                o=[AbilityFlag.GLOVE | AbilityFlag.SMASH | AbilityFlag.GLIDE | AbilityFlag.SWIM],
                n=None,
                u=[AbilityFlag.GLOVE | AbilityFlag.SMASH | AbilityFlag.GLIDE],
                s=None,
                token=[AbilityFlag.GLOVE | AbilityFlag.SMASH | AbilityFlag.GLIDE | AbilityFlag.SWIM],
            ),
            tokens=[
                TokenLocationData("Catch Rizzo", any_weapon_flag()),
                TokenLocationData("In the water by the start", [AbilityFlag.SWIM]),
                TokenLocationData("Ghost hunting", [AbilityFlag.GLOVE | AbilityFlag.SMASH | AbilityFlag.SPIN]),
                TokenLocationData("Shoot Beaker", [AbilityFlag.GLOVE | AbilityFlag.SMASH | AbilityFlag.GLIDE]),
                TokenLocationData(
                    "On a floating platform",
                    [AbilityFlag.GLOVE | AbilityFlag.SMASH | AbilityFlag.GLIDE | AbilityFlag.SWIM],
                ),
                TokenLocationData(
                    "In a hidden room next to the exit",
                    [AbilityFlag.GLOVE | AbilityFlag.SMASH | AbilityFlag.GLIDE | AbilityFlag.SWIM],
                ),
            ],
        ),
        two=LevelRegionData(
            name=LevelName.ICE_TO_MEETCHA,
            total_energy=580,
            energy=EnergyLocationData(
                half=[],
                full=[],
            ),
            bonus=BonusLocationData(
                b=[],
                o=[],
                n=[],
                u=[],
                s=[],
                token=[],
            ),
            tokens=[],
        ),
        three=LevelRegionData(
            name=LevelName.FOR_PETONS_SAKE,
            total_energy=600,
            energy=EnergyLocationData(
                half=[],
                full=[],
            ),
            bonus=BonusLocationData(
                b=[],
                o=[],
                n=[],
                u=[],
                s=[],
                token=[],
            ),
            tokens=[],
        ),
        boss=BossRegionData(LevelName.THE_MYSTERY_OF_THE_MASTER, None),
    ),
]

all_locations_table: list[MMARegion] = []
for group in level_groups:
    all_locations_table.extend(group.flatten())

# Maps region name to the region data definition
region_lookup: dict[str, MMARegion] = {region.name: region for region in all_locations_table}
non_boss_region_lookup: dict[str, MMARegion] = {
    region.name: region for region in all_locations_table if type(region) is MMALevelRegion
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
