from dataclasses import dataclass

from Options import OptionCounter, OptionSet, PerGameCommonOptions, Range, Toggle
from worlds.muppet_monster_adventure.items import filler_items_table, trap_items_table


class EnergyLocations(OptionSet):
    """Toggle individual Evil Energy check thresholds."""

    display_name = "Evil Energy Thresholds"
    valid_keys = ["50%", "100%"]
    default = ["50%", "100%"]


class BonusLocations(Toggle):
    """If enabled, each BONUS letter in regular levels will be a check."""

    display_name = "BONUS-sanity"
    default = True


class TokenLocations(Toggle):
    """If enabled, Muppet Tokens will be checks."""

    display_name = "Token-sanity"
    default = True


class BossGoal(Range):
    """Number of bosses required to be defeated to complete the game."""

    display_name = "Required Bosses"
    range_start = 1
    range_end = 5
    default = 5


class TrapRatio(Range):
    """
    Adjust the percentage of empty locations that will be filled with traps.
    The remaining locations will be populated with filler items.
    Setting this to zero will disable traps entirely.
    """

    display_name = "Trap Ratio"
    range_start = 0
    range_start = 100
    default = 10


class FillerWeights(OptionCounter):
    """
    Customize the chance of each filler item appearing in the multiworld.
    Setting a trap weight to 0 prevents it from being used.
    """

    display_name = "Filler Item Weights"
    min = 0
    valid_keys = sorted({item.name for item in filler_items_table})
    default = {item.name: 1 for item in filler_items_table}


class TrapWeights(OptionCounter):
    """
    Customize the chance of each trap appearing in the multiworld.
    Setting a trap weight to 0 prevents it from being used.
    """

    display_name = "Trap Weights"
    min = 0
    valid_keys = sorted({trap.name for trap in trap_items_table})
    default = {trap.name: 1 for trap in trap_items_table}


@dataclass
class MMAOptions(PerGameCommonOptions):
    energy: EnergyLocations
    bonus: BonusLocations
    goal: BossGoal
    trap_ratio: TrapRatio
    filler: FillerWeights
    traps: TrapWeights
