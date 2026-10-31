from dataclasses import dataclass

from Options import OptionCounter, OptionSet, PerGameCommonOptions, Range, Toggle

from .items import filler_items_table, trap_items_table
from .locations import EnergyAmount


class EnergyThresholds(OptionSet):
    """Toggle individual Evil Energy check thresholds."""

    display_name = "Evil Energy Thresholds"
    valid_keys = [it.value for it in EnergyAmount]
    default = {it.value: 1 for it in EnergyAmount}


class BonusLocations(Toggle):
    """If enabled, each BONUS letter in regular levels will be a check."""

    display_name = "BONUSsanity"
    default = True


class TokenLocations(Toggle):
    """If enabled, Muppet Tokens will be checks."""

    display_name = "Tokensanity"
    default = True


class BossGoal(Range):
    """Number of bosses required to be defeated to complete the game."""

    display_name = "Required Bosses"
    range_start = 1
    range_end = 6
    default = 6


class TrapRatio(Range):
    """
    Adjust the percentage of empty locations that will be filled with traps.
    The remaining locations will be populated with filler items.
    Setting this to zero will disable traps entirely.
    """

    display_name = "Trap Ratio"
    range_start = 0
    range_end = 100
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

class DisablePepeMessages(Toggle):
    """If enabled, Pepe will only talk to you, if he's running a mini-game, and minigames."""

    display_name = "Disable Pepe Messages"
    default = True

class DisableMinigameTokens(Toggle):
    """If enabled, will disable all minigame checks."""

    display_name = "Disable minigames"
    default = False 

class RewordMinigameMessages(Toggle):
    """If enabled, will remove the Mini-game explanation messages."""

    display_name = "Reword mini-game messages"
    default = True 

# TODO: progressive morphs option? the order in the game is Climb, Swim, Glide, Smash, Push
@dataclass
class MMAOptions(PerGameCommonOptions):
    energy_thresholds: EnergyThresholds
    bonus_sanity: BonusLocations
    token_sanity: TokenLocations
    goal: BossGoal
    trap_ratio: TrapRatio
    filler_weights: FillerWeights
    trap_weights: TrapWeights
    disable_minigames: DisableMinigameTokens
    disable_pepe_messages: DisablePepeMessages
    reword_minigame_messages: RewordMinigameMessages
