from AutoWorld import World

from BaseClasses import Item, Location

from .items import item_name_to_id
from .locations import all_locations_table

base_id: int = 25_899_560
game_name: str = "Muppet Monster Adventure"


class MMAItem(Item):
    game: str = game_name


class MMALocation(Location):
    game: str = game_name


class MuppetMonsterAdventureWorld(World):
    game = "Muppet Monster Adventure"

    # TODO: see blasphemous' locations and init for how i plan on generating location/item ids
    item_name_to_id = item_name_to_id(base_id)
    location_name_to_id = {item: (base_id + index) for index, item in enumerate(all_locations_table)}
    # item_name_groups = {group: names for _, group in enumerate(all_items_table)}

    def __init__(self, multiworld, player):
        super().__init__(multiworld, player)
