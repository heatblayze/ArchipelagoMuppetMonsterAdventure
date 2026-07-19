from BaseClasses import Item, Location
from worlds.AutoWorld import World

from .client import *  # noqa: F403
from .constants import base_id, game_name
from .items import item_name_groups, item_name_to_id
from .locations import location_name_groups, location_name_to_id


class MMAItem(Item):
    game: str = game_name


class MMALocation(Location):
    game: str = game_name


class MuppetMonsterAdventureWorld(World):
    game = game_name

    topology_present = False  # Levels can be played in any order.

    item_name_to_id = item_name_to_id(base_id)
    item_name_groups = item_name_groups()
    location_name_to_id = location_name_to_id(base_id)
    location_name_groups = location_name_groups()

    def __init__(self, multiworld, player):
        super().__init__(multiworld, player)
