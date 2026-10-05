from dataclasses import dataclass

from Options import OptionSet, PerGameCommonOptions


class EnergyLocations(OptionSet):
    """Enable/disable Evil Energy location thresholds."""

    display_name = "Evil Energy Locations"
    valid_keys = ["50%", "100%"]
    default = ["50%", "100%"]


@dataclass
class MMAOptions(PerGameCommonOptions):
    energy: EnergyLocations
