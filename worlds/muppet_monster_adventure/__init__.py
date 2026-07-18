from AutoWorld import World

from BaseClasses import Item, Location

mma_base_id: int = 25_899_560
mma_game_name: str = "Muppet Monster Adventure"


class MMAItem(Item):
    game: str = mma_game_name


class MMALocation(Location):
    game: str = mma_game_name


class MuppetMonsterAdventureWorld(World):
    game = "Muppet Monster Adventure"
