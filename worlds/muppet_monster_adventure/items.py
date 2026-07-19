from typing import NamedTuple

from BaseClasses import ItemClassification as IC


class MMAItemData(NamedTuple):
    classification: IC


abilities_table: dict[str, MMAItemData] = {
    "Climbing": MMAItemData(IC.progression),
    "Swimming": MMAItemData(IC.progression),
    "Gliding": MMAItemData(IC.progression),
    "Block Pushing": MMAItemData(IC.progression),
    "Smashing": MMAItemData(IC.progression),
    # TODO: figure out how to lock these (if possible)
    # "Power Glove": MMAItemData(IC.progression),
    # "Spin": MMAItemData(IC.progression),
}

levels_table: dict[str, MMAItemData] = {
    "Peacock Purgatory": MMAItemData(IC.progression),
    # TODO: other levels
}

all_items_table: dict[str, dict[str, MMAItemData]] = {
    "Abilities": abilities_table,
    "Levels": levels_table,
}


def item_name_to_id(base_id: int) -> dict[str, int]:
    """Converts all known items from their `[Type: [Name: Data]]` format into `[Name: ID]`,
    where `ID` is a deterministic value greater than `base_id`."""
    map: dict[str, int] = {}
    for group_idx, group_name in enumerate(all_items_table):
        for item_idx, item_name in enumerate(all_items_table[group_name]):
            map[item_name] = base_id + group_idx + item_idx
    return map


def item_name_groups() -> dict[str, set[str]]:
    """Converts all known items from their `[Type: [Name: Data]]` format into `[Type: [Name]]`."""
    map: dict[str, set[str]] = {}
    for _, group_name in enumerate(all_items_table):
        group: list[str] = []
        for _, item_name in enumerate(all_items_table[group_name]):
            group.append(item_name)
        map[group_name] = set(group)
    return map
