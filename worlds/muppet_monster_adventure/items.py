from typing import NamedTuple

from BaseClasses import ItemClassification as IC


class MMAItemData(NamedTuple):
    classification: IC


item_table: dict[str, MMAItemData] = {
    "Climbing": MMAItemData(IC.progression),
    "Swimming": MMAItemData(IC.progression),
    "Gliding": MMAItemData(IC.progression),
    "Block Pushing": MMAItemData(IC.progression),
    "Smashing": MMAItemData(IC.progression),
}
